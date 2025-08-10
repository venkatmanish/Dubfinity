from __future__ import annotations
from typing import List, Dict, Optional
import io, wave, numpy as np
import json
from pathlib import Path
import logging

from backend.services.smallest_service import SmallestClient
from backend.config import settings
from backend.processing.audio_utils import concat_wavs, apply_watermark, WatermarkCfg

logger = logging.getLogger(__name__)
cfg = settings()

# ---- voice mapping (actors -> voice_id) ----
VOICE_IDS_PATH = Path(cfg.VOICE_IDS_PATH)
if not VOICE_IDS_PATH.exists():
    logger.warning("voice_ids.json not found at %s; TTS will still run with sdk fallback tone.", VOICE_IDS_PATH)
    VOICE_IDS: Dict[str, str] = {}
else:
    try:
        VOICE_IDS = json.loads(VOICE_IDS_PATH.read_text())
    except Exception as e:
        logger.warning("Failed to read voice_ids.json (%s). Proceeding with empty mapping.", e)
        VOICE_IDS = {}

# ---- helpers ----
def _wav_bytes_to_array(wav_bytes: bytes) -> np.ndarray:
    buf = io.BytesIO(wav_bytes)
    with wave.open(buf, "rb") as wf:
        n = wf.getnframes()
        audio = np.frombuffer(wf.readframes(n), dtype="<i2").astype(np.float32) / 32768.0
        ch = wf.getnchannels()
        if ch > 1:
            audio = audio.reshape(-1, ch).mean(axis=1)
        return audio

def _array_to_wav_bytes(arr: np.ndarray, sr: int = 16000) -> bytes:
    arr = np.clip(arr, -1.0, 1.0)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
        wf.writeframes((arr * 32767).astype("<i2").tobytes())
    return buf.getvalue()

def _zeros_seconds(sec: float, sr: int = 16000) -> np.ndarray:
    if sec <= 0:
        return np.zeros(0, dtype=np.float32)
    n = int(max(0, round(sec * sr)))
    return np.zeros(n, dtype=np.float32)

class DubbingAgent:
    """
    Synthesizes per-segment audio and concatenates to a single WAV.
    - Uses actor->voice_id mapping from demos/demo_assets/voice_ids.json
    - Optional per-speaker mapping via speaker_to_actor
    - Optional timing preservation (insert silence between segments)
    - Optional audio watermark (demo-level)
    """

    def __init__(self, sdk: SmallestClient):
        self.sdk = sdk
        self.default_sr = 16000

    def _pick_voice_id(
        self,
        speaker_hint: Optional[str],
        speaker_to_actor: Optional[Dict[str, str]],
        segment_speaker: Optional[str],
    ) -> Optional[str]:
        """
        Priority:
          1) If speaker_to_actor is provided and segment has a speaker label, map to actor → voice_id
          2) If speaker_hint (single actor name) provided, use that → voice_id
          3) Fallback: first available voice in mapping (if any)
          4) None (SDK will still produce a dummy tone if voice_id is None or missing)
        """
        # 1) per-speaker mapping
        if speaker_to_actor and segment_speaker:
            actor = speaker_to_actor.get(segment_speaker)
            if actor and actor in VOICE_IDS:
                return VOICE_IDS[actor]

        # 2) single actor hint
        if speaker_hint and speaker_hint in VOICE_IDS:
            return VOICE_IDS[speaker_hint]

        # 3) first mapping
        if VOICE_IDS:
            return next(iter(VOICE_IDS.values()))

        # 4) nothing
        return None

    def synthesize_and_concat(
        self,
        segments: List[Dict],
        prosody: Dict,
        speaker_hint: Optional[str] = None,
        speaker_to_actor: Optional[Dict[str, str]] = None,  # e.g. {"spk1":"AamirKhan", "spk2":"AliaBhatt"}
        lang: Optional[str] = None,
        preserve_timing: bool = True,
        watermark: Optional[bool] = None,
    ) -> bytes:
        """
        segments: [{start, end, text, speaker? , tgt_lang?}, ...]
        prosody:  currently unused placeholder; wire to SDK params when supported
        """
        sr = self.default_sr
        if not segments:
            logger.info("DubbingAgent: no segments provided; returning 0-length WAV.")
            return _array_to_wav_bytes(np.zeros(0, dtype=np.float32), sr=sr)

        # Determine target language
        target_lang = lang or segments[0].get("tgt_lang") or cfg.languages.get("targets", ["te","en","kn"])[0]

        # Sort segments by start time if present (defensive)
        try:
            segments = sorted(segments, key=lambda s: float(s.get("start", 0.0)))
        except Exception:
            pass

        pieces: List[np.ndarray] = []

        # If preserving timing, we’ll keep a cursor of "current time" and pad with silence as needed.
        current_time = float(segments[0].get("start", 0.0)) if preserve_timing else 0.0

        for seg in segments:
            text = seg.get("text", "") or ""
            seg_start = float(seg.get("start", 0.0))
            seg_end = float(seg.get("end", seg_start))
            speaker = seg.get("speaker")

            # Timing gap padding
            if preserve_timing:
                gap = max(0.0, seg_start - current_time)
                if gap > 0.0:
                    pieces.append(_zeros_seconds(gap, sr=sr))
                    current_time += gap

            # Choose voice per segment
            voice_id = self._pick_voice_id(
                speaker_hint=speaker_hint,
                speaker_to_actor=speaker_to_actor,
                segment_speaker=speaker,
            )

            # Synthesize
            try:
                audio_bytes = self.sdk.synthesize(text=text, voice_id=voice_id or "", lang=target_lang)
            except Exception as e:
                logger.warning("Synth failed for segment (%s); using silence. err=%s", text[:24], e)
                audio_bytes = _array_to_wav_bytes(_zeros_seconds(0.1, sr=sr), sr=sr)

            audio_arr = _wav_bytes_to_array(audio_bytes)
            pieces.append(audio_arr)

            # Advance current_time by either the segment nominal length or synthesized duration
            if preserve_timing:
                # Prefer nominal segment duration; fall back to synthesized length
                nominal = max(0.0, seg_end - seg_start)
                synth_len_sec = len(audio_arr) / float(sr)
                advance = nominal if nominal > 0 else synth_len_sec
                current_time += advance

        # Stitch together
        stitched = concat_wavs(pieces)

        # Optional watermark
        wm_enabled_cfg = bool(cfg.modes.get("watermark_enabled", True))
        wm_enabled = wm_enabled_cfg if watermark is None else bool(watermark)
        wm_cfg = WatermarkCfg(enabled=wm_enabled, strength=0.04, freq_hz=18000.0)
        if wm_enabled:
            stitched = apply_watermark(stitched, sr=sr, cfg=wm_cfg)

        return _array_to_wav_bytes(stitched, sr=sr)
