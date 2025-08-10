from __future__ import annotations
"""
Prosody helpers: crude per-frame energy, zero-crossing-based pitch estimate,
and mapping to simple TTS controls (rate, energy multiplier).
"""

from typing import Dict, Tuple
import numpy as np

def frame_energy(x: np.ndarray, sr: int, win_ms: float = 25.0, hop_ms: float = 10.0) -> np.ndarray:
    """Short-time energy."""
    win = int(sr * win_ms / 1000.0)
    hop = int(sr * hop_ms / 1000.0)
    if win <= 0 or hop <= 0 or len(x) < win:
        return np.array([], dtype=np.float32)
    frames = []
    for i in range(0, len(x) - win + 1, hop):
        f = x[i:i+win]
        frames.append(np.sqrt(np.mean(f**2) + 1e-8))
    return np.asarray(frames, dtype=np.float32)

def zero_crossing_pitch(x: np.ndarray, sr: int, min_f0: float = 80.0, max_f0: float = 300.0) -> float:
    """
    Extremely rough pitch estimate via zero-crossings (use only for heuristics).
    """
    if len(x) == 0:
        return 0.0
    # count zero crossings
    zc = np.where(np.diff(np.signbit(x)))[0]
    if len(zc) < 2:
        return 0.0
    # average period between crossings (2 crossings per cycle)
    periods = np.diff(zc) / float(sr)
    if len(periods) == 0:
        return 0.0
    avg_period = float(np.median(periods) * 2.0)
    if avg_period <= 0:
        return 0.0
    f0 = 1.0 / avg_period
    if f0 < min_f0 or f0 > max_f0:
        return 0.0
    return float(f0)

def prosody_summary(x: np.ndarray, sr: int) -> Dict:
    """
    Summarize simple prosody: average energy and a crude pitch estimate.
    """
    eng = frame_energy(x, sr)
    f0 = zero_crossing_pitch(x, sr)
    return {
        "avg_energy": float(np.mean(eng)) if eng.size else 0.0,
        "pitch_est_hz": float(f0),
    }

def map_prosody_to_tts_controls(summary: Dict) -> Dict:
    """
    Map prosody summary to basic TTS knobs (rate multiplier, energy).
    """
    energy = summary.get("avg_energy", 0.0)
    rate = 1.0
    if energy > 0.08:
        rate = 1.08
    elif energy < 0.02:
        rate = 0.94
    return {
        "rate": round(rate, 2),
        "energy": round(float(energy), 4),
        "pitch_hint_hz": round(float(summary.get("pitch_est_hz", 0.0)), 1)
    }
