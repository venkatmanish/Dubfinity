from __future__ import annotations
import io
import json
import math
import logging
from pathlib import Path
from typing import Optional, AsyncIterable

import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from backend.config import settings
from backend.services.smallest_service import SmallestClient
from backend.agents.orchestrator_agent import OrchestratorAgent

router = APIRouter()
logger = logging.getLogger(__name__)
cfg = settings()

_sdk = SmallestClient()
_orch = OrchestratorAgent()

# --------- helpers --------- #

def _dummy_wav(seconds=1.0, sr=16000) -> bytes:
    import wave
    t = np.linspace(0, seconds, int(sr * seconds), endpoint=False)
    tone = 0.12 * np.sin(2 * math.pi * 660 * t)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes((tone * 32767).astype("<i2").tobytes())
    return buf.getvalue()

def _load_voice_map() -> dict[str, str]:
    path = Path(getattr(cfg, "VOICE_IDS_PATH", "demos/demo_assets/voice_ids.json"))
    if not path.exists():
        logger.warning("voice_ids.json not found at %s", path)
        return {}
    try:
        import json as _json
        return _json.loads(path.read_text())
    except Exception as e:
        logger.warning("Failed to parse voice_ids.json: %s", e)
        return {}

_VOICE_MAP = _load_voice_map()

def _resolve_voice_id(actor: Optional[str], voice_id: Optional[str]) -> Optional[str]:
    if voice_id:
        return voice_id
    if actor and actor in _VOICE_MAP:
        return _VOICE_MAP[actor]
    return next(iter(_VOICE_MAP.values())) if _VOICE_MAP else None

async def _send_error(ws: WebSocket, detail: str):
    try:
        await ws.send_text(json.dumps({"event": "error", "detail": detail}))
    except Exception:
        pass

# --------- WebSocket: token → speech --------- #

@router.websocket("/ws/llm_tts")
async def ws_llm_tts(
    ws: WebSocket,
    actor: Optional[str] = Query(None, description="Actor name from voice_ids.json"),
    voice_id: Optional[str] = Query(None, description="Direct voice id (overrides actor)"),
    language: Optional[str] = Query(None, description="Target language code (e.g., te|en|kn)"),
    provider: Optional[str] = Query("groq", description="LLM provider hint (for logs only)"),
    model: Optional[str] = Query("llama3-8b-8192", description="LLM model hint (for logs only)"),
):
    """
    Token→Speech streaming.
    Protocol:
      1) Client connects with query params (actor/voice_id/lang).
      2) Client sends JSON messages of the form:
            {"prompt":"...", "stream_tokens": true}
         or incremental tokens:
            {"token":"कुछ", "is_final": false}
      3) Server streams **binary audio/wav** chunks as they are synthesized.
      4) Server emits {"event":"done"} when a request completes (client may send another request).
    """
    await ws.accept()
    v_id = _resolve_voice_id(actor, voice_id)
    if not v_id:
        await _send_error(ws, "no voice available: seed voices or pass a voice_id")
        await ws.close(code=1011)
        return

    lang = language or cfg.languages.get("targets", ["te", "en", "kn"])[0]
    logger.info("ws/llm_tts connected (provider=%s model=%s, voice=%s, lang=%s)", provider, model, v_id, lang)

    # Check if SmallestClient has a token→speech streamer
    has_token_stream = hasattr(_sdk, "stream_token_tts") and callable(getattr(_sdk, "stream_token_tts"))

    try:
        while True:
            try:
                msg = await ws.receive_text()
            except WebSocketDisconnect:
                break
            except Exception:
                # ignore malformed frames; keep the socket alive
                continue

            try:
                payload = json.loads(msg)
            except Exception:
                await _send_error(ws, "invalid JSON")
                continue

            # Two modes:
            #  A) One-shot prompt (the server handles tokenization/LLM streaming internally)
            #  B) Client pushes incremental tokens (token field)
            prompt = (payload.get("prompt") or "").strip()
            token = (payload.get("token") or "").strip()
            is_final = bool(payload.get("is_final", False))

            # Orchestrate for realtime
            decision = _orch.decide(text_len=len(prompt or token), realtime=True)

            if has_token_stream:
                # ---- Preferred: true incremental token→speech path ----
                try:
                    if prompt:
                        # Single request where the server handles LLM streaming internally (sdk decides)
                        async for audio_chunk in _sdk.stream_token_tts(
                            prompt=prompt,
                            voice_id=v_id,
                            lang=lang,
                            model=decision.tts_model,
                            speed=decision.speed,
                        ):
                            await ws.send_bytes(audio_chunk)
                    elif token:
                        # Client-driven token-by-token streaming
                        async for audio_chunk in _sdk.stream_token_tts(
                            token=token,
                            is_final=is_final,
                            voice_id=v_id,
                            lang=lang,
                            model=decision.tts_model,
                            speed=decision.speed,
                        ):
                            await ws.send_bytes(audio_chunk)
                    else:
                        await _send_error(ws, "provide either 'prompt' or 'token'")
                        continue

                    await ws.send_text(json.dumps({"event": "done"}))

                except Exception as e:
                    logger.exception("ws/llm_tts token stream failed: %s", e)
                    await _send_error(ws, f"stream failed: {e}")

            else:
                # ---- Fallback: return a single dummy tone chunk (keeps demo flowing) ----
                wav = _dummy_wav(1.2)
                chunk = 1920
                for i in range(0, len(wav), chunk):
                    await ws.send_bytes(wav[i : i + chunk])
                await ws.send_text(json.dumps({"event": "done", "fallback": True}))
    finally:
        try:
            await ws.close()
        except Exception:
            pass
