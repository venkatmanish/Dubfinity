# backend/routes/tts.py
from __future__ import annotations
import json
import logging
import time
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Body, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import Response

from backend.config import settings
from backend.models.tts_models import TTSRequest, TTSResponse
from backend.services.smallest_service import SmallestClient
from backend.agents.orchestrator_agent import OrchestratorAgent
from backend.metrics.metrics_collector import record_request_metrics

logger = logging.getLogger(__name__)
router = APIRouter()

cfg = settings()
_sdk = SmallestClient()
_orch = OrchestratorAgent()

# Load actor -> voice_id mapping (same file used by DubbingAgent)
def _load_voice_map() -> dict[str, str]:
    path = Path(cfg.VOICE_IDS_PATH)
    if not path.exists():
        logger.warning("voice_ids.json not found at %s", path)
        return {}
    try:
        return json.loads(path.read_text())
    except Exception as e:
        logger.warning("Failed to parse voice_ids.json: %s", e)
        return {}

_VOICE_MAP = _load_voice_map()


def _resolve_voice_id(actor: Optional[str], voice_id: Optional[str]) -> Optional[str]:
    if voice_id:
        return voice_id
    if actor and actor in _VOICE_MAP:
        return _VOICE_MAP[actor]
    # fallback: first voice if any
    return next(iter(_VOICE_MAP.values())) if _VOICE_MAP else None


def _split_text(text: str, max_chars: int) -> List[str]:
    """Greedy sentence-ish splitter with a char budget."""
    import re
    text = text.strip()
    if not text:
        return []
    # split on sentence boundaries first
    parts = re.split(r"(?<=[\.\?\!।])\s+", text)
    chunks: List[str] = []
    buf = ""
    for p in parts:
        if not p:
            continue
        if len(buf) + (1 if buf else 0) + len(p) <= max_chars:
            buf = f"{buf} {p}".strip() if buf else p
        else:
            if buf:
                chunks.append(buf)
            # if single sentence is longer than budget, hard wrap
            if len(p) > max_chars:
                for i in range(0, len(p), max_chars):
                    chunks.append(p[i : i + max_chars])
                buf = ""
            else:
                buf = p
    if buf:
        chunks.append(buf)
    return chunks


@router.post("/v1/tts", summary="Synthesize text to speech (audio/wav)")
def tts(req: TTSRequest = Body(...)) -> Response:
    """
    Returns raw **audio/wav** bytes so the client can play them directly.
    Provide either `actor` (name from voice_ids.json) or `voice_id`.
    """
    text = (req.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text is required")

    voice_id = _resolve_voice_id(req.actor, req.voice_id)
    if not voice_id:
        raise HTTPException(status_code=400, detail="No voice available: provide actor or voice_id, or seed voices")

    # Orchestrator decides model + chunking
    decision = _orch.decide(text_len=len(text), realtime=False)
    chunks = _split_text(text, decision.max_chars_per_chunk)

    audio_pieces: List[bytes] = []
    err: Optional[str] = None
    t0 = time.perf_counter()

    try:
        for idx, piece in enumerate(chunks or [text]):
            with _orch.time_and_observe():
                wav_bytes = _sdk.synthesize(
                    text=piece,
                    voice_id=voice_id,
                    lang=req.language or cfg.languages.get("targets", ["te", "en", "kn"])[0],
                    model=decision.tts_model,
                    speed=req.speed or decision.speed,
                    enhancement=req.enhancement if req.enhancement is not None else decision.enhancement,
                )
            audio_pieces.append(wav_bytes)
    except Exception as e:
        logger.exception("TTS synth failed: %s", e)
        err = str(e)

    dt = time.perf_counter() - t0
    # basic metrics
    record_request_metrics(endpoint="/v1/tts", method="POST", status_code=200 if not err else 500, latency=dt)

    if err:
        raise HTTPException(status_code=500, detail=f"TTS failed: {err}")

    # Concatenate WAVs safely (let SDK return full WAVs; we re-mux by naive concat if same params)
    # For hackathon simplicity, we return the first chunk if multiple; or you can
    # swap in your audio_utils.concat_wavs_bytes(pieces) if you’ve implemented it.
    if len(audio_pieces) == 1:
        out = audio_pieces[0]
    else:
        # optional: use backend.processing.audio_utils.concat_wavs if available
        try:
            from backend.processing.audio_utils import concat_wavs, wav_bytes_to_array, array_to_wav_bytes
            import numpy as np
            arrays = [wav_bytes_to_array(b) for b in audio_pieces]
            arr = concat_wavs(arrays)
            out = array_to_wav_bytes(arr, sr=16000)
        except Exception:
            # naive fallback: byte concat; some players may still handle it
            out = b"".join(audio_pieces)

    filename = "tts.wav" if req.format == "wav" else "tts.wav"  # mp3 transcode not wired here
    headers = {"Content-Disposition": f'attachment; filename="{filename}"', "X-Orchestrator-Model": decision.tts_model}
    return Response(content=out, media_type="audio/wav", headers=headers)


# ---------------------- WebSocket streaming ---------------------- #

@router.websocket("/ws/tts")
async def ws_tts(
    ws: WebSocket,
    actor: Optional[str] = Query(None, description="Actor name from voice_ids.json"),
    voice_id: Optional[str] = Query(None, description="Override voice id"),
    language: Optional[str] = Query(None, description="Target language code"),
    speed: Optional[float] = Query(None, ge=0.5, le=2.0, description="Speech speed multiplier"),
):
    """
    Streaming TTS. Protocol:
      - Client connects with query params (actor/voice_id/lang/speed).
      - Client sends one JSON text frame: {"text": "..."} (you can send multiple messages for multiple synths).
      - Server streams **binary** frames (WAV chunks) as they are synthesized.
      - Server finally sends a text frame: {"event":"done"}.

    Example (client):
      ws.send(JSON.stringify({text: "Hello world. Sentence two."}))
      // receive binary blobs (audio/wav) …
      // receive {"event":"done"} then close or send another message
    """
    await ws.accept()
    try:
        resolved_voice_id = _resolve_voice_id(actor, voice_id)
        if not resolved_voice_id:
            await ws.send_text(json.dumps({"event": "error", "detail": "no voice available"}))
            await ws.close(code=1011)
            return

        while True:
            try:
                msg = await ws.receive_text()
            except WebSocketDisconnect:
                break
            except Exception:
                # Could be binary; ignore and continue
                continue

            try:
                payload = json.loads(msg)
                text = (payload.get("text") or "").strip()
                if not text:
                    await ws.send_text(json.dumps({"event": "error", "detail": "empty text"}))
                    continue

                # Orchestrate for real-time stream
                decision = _orch.decide(text_len=len(text), realtime=True)
                chunks = _split_text(text, decision.max_chars_per_chunk)

                for idx, piece in enumerate(chunks or [text]):
                    t0 = time.perf_counter()
                    with _orch.time_and_observe():
                        wav_bytes = _sdk.synthesize(
                            text=piece,
                            voice_id=resolved_voice_id,
                            lang=language or cfg.languages.get("targets", ["te", "en", "kn"])[0],
                            model=decision.tts_model,
                            speed=speed or decision.speed,
                            enhancement=decision.enhancement,
                        )
                    # Stream this chunk as binary
                    await ws.send_bytes(wav_bytes)
                    # lightweight per-chunk metric
                    dt = time.perf_counter() - t0
                    record_request_metrics(endpoint="/ws/tts", method="WS", status_code=101, latency=dt)

                await ws.send_text(json.dumps({"event": "done"}))

            except Exception as e:
                logger.exception("ws/tts failed: %s", e)
                try:
                    await ws.send_text(json.dumps({"event": "error", "detail": str(e)}))
                except Exception:
                    pass

    finally:
        try:
            await ws.close()
        except Exception:
            pass
