from __future__ import annotations
from typing import Iterable, List, Optional
import logging
import time

from backend.services.smallest_service import SmallestClient
from backend.agents.orchestrator_agent import OrchestratorAgent

logger = logging.getLogger(__name__)

def _split_text(text: str, max_chars: int) -> List[str]:
    """Greedy sentence-ish splitter with a char budget (same as /v1/tts route)."""
    import re
    text = (text or "").strip()
    if not text:
        return []
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
            if len(p) > max_chars:
                for i in range(0, len(p), max_chars):
                    chunks.append(p[i : i + max_chars])
                buf = ""
            else:
                buf = p
    if buf:
        chunks.append(buf)
    return chunks


class RealTimeAudioPipeline:
    """
    Real-time-ish text→speech streaming pipeline.

    Strategy:
      - Use OrchestratorAgent(decide(..., realtime=True)) to choose fast model + chunk size
      - If SDK supports true streaming (client.stream_tts), use it.
      - Else synthesize per-chunk and yield WAV chunks sequentially.
    """

    def __init__(self, sdk: SmallestClient, orchestrator: Optional[OrchestratorAgent] = None):
        self.sdk = sdk
        self.orch = orchestrator or OrchestratorAgent()

    def stream_text(
        self,
        text: str,
        voice_id: str,
        lang: str = "te",
        speed: Optional[float] = None,
    ) -> Iterable[bytes]:
        """
        Yields WAV chunks (bytes). Caller can write them to a WS or HTTP chunked response.

        NOTE:
        - `voice_id` must be a valid Smallest voice ID (resolve actor->voice_id at the route layer).
        - If the SDK or key is missing, SmallestClient.synthesize should fall back to a dummy tone.
        """
        decision = self.orch.decide(text_len=len(text or ""), realtime=True)
        max_chars = decision.max_chars_per_chunk
        chunks = _split_text(text, max_chars) or [text]

        for piece in chunks:
            t0 = time.perf_counter()
            try:
                # Preferred: true stream from SDK (if implemented in your wrapper)
                if hasattr(self.sdk, "stream_tts") and callable(self.sdk.stream_tts):
                    # stream_tts should itself yield bytes; we re-yield to the caller
                    for b in self.sdk.stream_tts(
                        text=piece,
                        voice_id=voice_id,
                        lang=lang,
                        model=decision.tts_model,
                        speed=speed or decision.speed,
                        enhancement=decision.enhancement,
                        chunk=1920,  # frame size hint; adjust per SDK
                    ):
                        yield b
                else:
                    # Fallback: synthesize a full small chunk; still feels streaming to the client
                    with self.orch.time_and_observe():
                        wav = self.sdk.synthesize(
                            text=piece,
                            voice_id=voice_id,
                            lang=lang,
                            model=decision.tts_model,
                            speed=speed or decision.speed,
                            enhancement=decision.enhancement,
                        )
                    yield wav
            except Exception as e:
                logger.warning("RealTimeAudioPipeline: synth failed for chunk (%s…): %s", piece[:24], e)
                # Yield nothing for this chunk; continue
                continue

            # let orchestrator learn (already learned via context manager in fallback path;
            # for the true streaming path, sample a tiny latency per chunk)
            dt = time.perf_counter() - t0
            if dt > 0:
                self.orch.observe_latency_seconds(dt)
