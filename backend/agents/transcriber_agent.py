from __future__ import annotations
from typing import List, Dict, Optional
import logging
import io
import tempfile
from pathlib import Path

import numpy as np

# audio decode (pure-Python)
import soundfile as sf

logger = logging.getLogger(__name__)

# Optional: faster-whisper
try:
    from faster_whisper import WhisperModel  # type: ignore
    _HAS_WHISPER = True
except Exception:
    _HAS_WHISPER = False


class TranscriberAgent:
    """
    ASR + lightweight diarization/timestamps.
    If faster-whisper is available, use it; otherwise:
      - produce a single segment covering the whole audio
    Diarization is a simple placeholder (alternating labels) to keep deps light.
    """

    def __init__(self, src_lang: str = "hi", model_size: str = "small"):
        self.src_lang = src_lang
        self.model_size = model_size
        self._whisper = None
        if _HAS_WHISPER:
            try:
                self._whisper = WhisperModel(model_size, compute_type="int8")
            except Exception as e:
                logger.warning("TranscriberAgent: Whisper init failed: %s", e)
                self._whisper = None

    @property
    def has_whisper(self) -> bool:
        return self._whisper is not None

    # ---------- utils ---------- #
    def _bytes_to_array(self, wav_bytes: bytes) -> tuple[np.ndarray, int]:
        buf = io.BytesIO(wav_bytes)
        audio, sr = sf.read(buf, always_2d=False)
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        audio = audio.astype(np.float32)
        return audio, int(sr)

    def _duration_sec(self, wav_bytes: bytes) -> float:
        try:
            x, sr = self._bytes_to_array(wav_bytes)
            return max(0.01, len(x) / float(sr))
        except Exception:
            return 1.0

    # ---------- public APIs ---------- #
    def transcribe_segments(self, wav_bytes: bytes, src_lang: Optional[str] = None) -> List[Dict]:
        """
        ASR directly from bytes. Returns a list of {start,end,text,speaker}.
        """
        lang = src_lang or self.src_lang

        if self._whisper:
            # Try numpy array path first; fallback to temp file if needed
            try:
                arr, sr = self._bytes_to_array(wav_bytes)
                segs, _ = self._whisper.transcribe(arr, language=lang, vad_filter=True)
            except Exception as e_np:
                logger.debug("Whisper np-array path failed, retrying via temp file: %s", e_np)
                with tempfile.NamedTemporaryFile(delete=True, suffix=".wav") as tmp:
                    tmp.write(wav_bytes)
                    tmp.flush()
                    segs, _ = self._whisper.transcribe(tmp.name, language=lang, vad_filter=True)

            out: List[Dict] = []
            spk_toggle = 0
            for s in segs:
                text = (getattr(s, "text", "") or "").strip()
                start = float(getattr(s, "start", 0.0) or 0.0)
                end = float(getattr(s, "end", start) or start)
                if not text and end <= start:
                    continue
                spk = f"spk{1 + (spk_toggle % 2)}"  # simple alternating labels
                spk_toggle += 1
                out.append({"start": start, "end": end, "text": text, "speaker": spk})
            if out:
                return out

        # Fallback: one whole-segment with empty text (enables downstream testing)
        dur = self._duration_sec(wav_bytes)
        return [{"start": 0.0, "end": dur, "text": "", "speaker": "spk1"}]

    def transcribe_with_diarization(self, audio_path: str, src_lang: Optional[str] = None) -> List[Dict]:
        """
        ASR from file path. Returns {start,end,text,speaker} list.
        """
        lang = src_lang or self.src_lang

        if self._whisper:
            try:
                segs, _ = self._whisper.transcribe(audio_path, language=lang, vad_filter=True)
                out: List[Dict] = []
                spk_toggle = 0
                for s in segs:
                    text = (getattr(s, "text", "") or "").strip()
                    start = float(getattr(s, "start", 0.0) or 0.0)
                    end = float(getattr(s, "end", start) or start)
                    if not text and end <= start:
                        continue
                    spk = f"spk{1 + (spk_toggle % 2)}"
                    spk_toggle += 1
                    out.append({"start": start, "end": end, "text": text, "speaker": spk})
                if out:
                    return out
            except Exception as e:
                logger.warning("TranscriberAgent: whisper path ASR failed: %s", e)

        # Fallback: read bytes and return one segment with duration
        try:
            wav_bytes = Path(audio_path).read_bytes()
        except Exception:
            wav_bytes = b""
        dur = self._duration_sec(wav_bytes)
        return [{"start": 0.0, "end": dur, "text": "", "speaker": "spk1"}]
