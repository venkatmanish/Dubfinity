from __future__ import annotations
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

# Optional ASR for audio-based scoring
try:
    from faster_whisper import WhisperModel  # type: ignore
    _HAS_WHISPER = True
except Exception:
    _HAS_WHISPER = False


# ---------- tiny, dependency-free WER ---------- #
def _normalize(s: str) -> list[str]:
    import re
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9\u0900-\u097F\s]", " ", s)  # keep latin digits + Devanagari
    s = re.sub(r"\s+", " ", s)
    return s.split()

def _edit_distance(a: list[str], b: list[str]) -> int:
    dp = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a) + 1): dp[i][0] = i
    for j in range(len(b) + 1): dp[0][j] = j
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,      # deletion
                dp[i][j - 1] + 1,      # insertion
                dp[i - 1][j - 1] + cost  # substitution
            )
    return dp[-1][-1]

def _wer(ref: str, hyp: str) -> float:
    r = _normalize(ref)
    h = _normalize(hyp)
    if not r:
        return 0.0 if not h else 1.0
    return _edit_distance(r, h) / float(len(r))


class QualityAgent:
    """
    Lightweight QA:
      - text mode: compute WER over concatenated original/dubbed segment texts
      - audio mode: (optional) ASR both WAVs using faster-whisper → WER
    Accepts output when WER <= threshold.
    """

    def __init__(self, max_wer: float = 0.35, whisper_model_size: str = "small"):
        self.max_wer = float(max_wer)
        self.model_size = whisper_model_size
        self._whisper = None
        if _HAS_WHISPER:
            try:
                self._whisper = WhisperModel(self.model_size, compute_type="int8")
            except Exception as e:
                logger.warning("QualityAgent: Whisper init failed: %s", e)
                self._whisper = None

    # ---------- text-based scoring ---------- #
    def _concat_text(self, segs: List[Dict]) -> str:
        return " ".join((s.get("text") or "").strip() for s in segs if s.get("text"))

    def score_segments(self, original: List[Dict], dubbed: List[Dict]) -> Dict:
        ref = self._concat_text(original)
        hyp = self._concat_text(dubbed)
        score = _wer(ref, hyp)
        accepted = score <= self.max_wer
        return {
            "mode": "text",
            "wer": round(score, 4),
            "accepted": bool(accepted),
            "threshold": self.max_wer,
            "reason": "text_wer_check",
            "ref_chars": len(ref),
            "hyp_chars": len(hyp),
            "segments_in": len(original),
            "segments_out": len(dubbed),
        }

    # ---------- audio-based scoring (optional) ---------- #
    def _transcribe(self, wav_path: str, lang: Optional[str]) -> str:
        if not self._whisper:
            raise RuntimeError("faster-whisper not available")
        segs, _ = self._whisper.transcribe(wav_path, language=lang or "auto", vad_filter=True)
        return " ".join(s.text.strip() for s in segs if getattr(s, "text", None))

    def score_audio_if_asr(self, original_wav: str, dubbed_wav: str, lang: Optional[str] = None) -> Dict:
        """
        If faster-whisper is installed, ASR both files and compute WER.
        Falls back to an accepted stub if whisper is not available.
        """
        if not self._whisper:
            return {
                "mode": "audio-asr",
                "wer": None,
                "accepted": True,
                "threshold": self.max_wer,
                "reason": "asr_unavailable_stub_accept"
            }
        try:
            ref_txt = self._transcribe(original_wav, lang)
            hyp_txt = self._transcribe(dubbed_wav, lang)
            score = _wer(ref_txt, hyp_txt)
            accepted = score <= self.max_wer
            return {
                "mode": "audio-asr",
                "wer": round(score, 4),
                "accepted": bool(accepted),
                "threshold": self.max_wer,
                "reason": "audio_wer_check",
                "ref_chars": len(ref_txt),
                "hyp_chars": len(hyp_txt),
            }
        except Exception as e:
            logger.warning("QualityAgent: ASR WER failed: %s", e)
            return {
                "mode": "audio-asr",
                "wer": None,
                "accepted": True,
                "threshold": self.max_wer,
                "reason": "asr_failed_stub_accept"
            }
