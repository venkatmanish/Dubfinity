from __future__ import annotations
"""
Audio helpers: load/save, resample, mono mixdown, silence trim, loudness normalize,
simple denoise (high-pass + soft gate), concatenation, and a tiny watermark stub.

Dependencies: numpy, soundfile (already in requirements).
"""

from dataclasses import dataclass
from typing import Tuple, List, Optional
import io, wave
import numpy as np
import soundfile as sf


# ----------------------------- I/O ----------------------------- #

def load_wav_bytes(wav_bytes: bytes) -> Tuple[np.ndarray, int]:
    """Read WAV/PCM bytes -> (mono float32 in [-1,1], samplerate)."""
    buf = io.BytesIO(wav_bytes)
    x, sr = sf.read(buf, always_2d=False)
    if x.ndim > 1:
        x = x.mean(axis=1)
    x = x.astype(np.float32)
    # clip any stray values
    x = np.clip(x, -1.0, 1.0)
    return x, sr


def save_wav_bytes(x: np.ndarray, sr: int = 16000) -> bytes:
    """(mono float32, sr) -> WAV/PCM16 bytes."""
    x = np.asarray(x, dtype=np.float32)
    x = np.clip(x, -1.0, 1.0)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes((x * 32767.0).astype("<i2").tobytes())
    return buf.getvalue()


# --------------------------- Resample -------------------------- #

def _linear_resample(x: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
    """Tiny linear resampler (good enough for demo paths)."""
    if sr_in == sr_out or len(x) == 0:
        return x.astype(np.float32)
    t_in = np.linspace(0, 1, num=len(x), endpoint=False)
    n_out = int(np.floor(len(x) * sr_out / sr_in))
    t_out = np.linspace(0, 1, num=n_out, endpoint=False)
    y = np.interp(t_out, t_in, x).astype(np.float32)
    return y


def to_mono_16k(x: np.ndarray, sr: int) -> Tuple[np.ndarray, int]:
    """Return mono 16 kHz version of x."""
    if x.ndim > 1:
        x = x.mean(axis=1)
    y = _linear_resample(x.astype(np.float32), sr, 16000)
    return y, 16000


# ------------------------- Basic filters ----------------------- #

def highpass(x: np.ndarray, sr: int, cutoff_hz: float = 80.0) -> np.ndarray:
    """One-pole high-pass (very light denoise / rumble removal)."""
    if len(x) == 0:
        return x
    rc = 1.0 / (2.0 * np.pi * cutoff_hz)
    dt = 1.0 / float(sr)
    alpha = rc / (rc + dt)
    y = np.zeros_like(x, dtype=np.float32)
    prev_y = 0.0
    prev_x = x[0]
    for i in range(len(x)):
        y[i] = alpha * (prev_y + x[i] - prev_x)
        prev_y = y[i]
        prev_x = x[i]
    return y


def soft_gate(x: np.ndarray, threshold_db: float = -40.0, ratio: float = 4.0) -> np.ndarray:
    """
    Primitive downward expander: attenuates frames below threshold.
    Not a full gate; keeps artifacts low for speech.
    """
    if len(x) == 0:
        return x
    eps = 1e-8
    frame = 256
    out = x.copy()
    for i in range(0, len(x), frame):
        seg = x[i:i+frame]
        rms = np.sqrt(np.mean(seg**2) + eps)
        db = 20*np.log10(rms + eps)
        if db < threshold_db:
            gain = 10**(((db - threshold_db) / ratio) / 20.0)
            out[i:i+frame] *= gain
    return out


# ------------------------- Silence trim ------------------------ #

def trim_silence(x: np.ndarray, sr: int, thresh_db: float = -40.0,
                 head_sec: float = 0.3, tail_sec: float = 0.35) -> np.ndarray:
    """
    Remove leading/trailing sections where RMS < thresh_db for at least head/tail sec.
    """
    if len(x) == 0:
        return x
    eps = 1e-8
    frame = max(1, int(0.02 * sr))   # 20 ms
    power = np.sqrt(np.convolve(x**2, np.ones(frame)/frame, mode="same") + eps)
    db = 20*np.log10(power + eps)

    # head
    head_frames = int(head_sec * sr)
    start = 0
    while start < len(x) and start < head_frames and db[start] < thresh_db:
        start += 1

    # tail
    tail_frames = int(tail_sec * sr)
    end = len(x) - 1
    while end >= 0 and (len(x) - end) < tail_frames and db[end] < thresh_db:
        end -= 1

    if start >= end:
        return np.zeros(0, dtype=np.float32)
    return x[start:end+1].astype(np.float32)


# ----------------------- Loudness normalize -------------------- #

def normalize_rms(x: np.ndarray, target_dbfs: float = -20.0, limit_dbfs: float = -1.0) -> np.ndarray:
    """
    Normalize to target RMS, then clip/limit to limit_dbfs.
    """
    if len(x) == 0:
        return x
    eps = 1e-8
    rms = float(np.sqrt(np.mean(np.square(x)) + eps))
    cur_db = 20*np.log10(rms + eps)
    gain_db = target_dbfs - cur_db
    y = x * (10**(gain_db / 20.0))

    peak = np.max(np.abs(y)) + eps
    peak_db = 20*np.log10(peak)
    if peak_db > limit_dbfs:
        y *= 10**((limit_dbfs - peak_db) / 20.0)
    return np.clip(y, -1.0, 1.0).astype(np.float32)


# --------------------------- Denoise --------------------------- #

def light_denoise(x: np.ndarray, sr: int) -> np.ndarray:
    """
    Very light denoise: high-pass + soft gate. Keeps speech artifacts low.
    """
    y = highpass(x, sr, cutoff_hz=80.0)
    y = soft_gate(y, threshold_db=-42.0, ratio=6.0)
    return y.astype(np.float32)


# -------------------------- Watermark -------------------------- #

@dataclass
class WatermarkCfg:
    strength: float = 0.05     # 0..1 (very low!)
    freq_hz: float = 18000.0   # near-inaudible on many speakers
    enabled: bool = False

def apply_watermark(x: np.ndarray, sr: int, cfg: Optional[WatermarkCfg]) -> np.ndarray:
    """
    Placeholder watermark: add a very low-level high-freq tone.
    (For demo only; replace with a proper watermarking scheme if needed.)
    """
    if not cfg or not cfg.enabled or cfg.strength <= 0.0:
        return x
    t = np.linspace(0, len(x) / sr, num=len(x), endpoint=False)
    tone = np.sin(2*np.pi*cfg.freq_hz * t).astype(np.float32)
    y = np.clip(x + cfg.strength * tone, -1.0, 1.0)
    return y.astype(np.float32)


# ------------------------- Concatenation ----------------------- #

def concat_wavs(parts: List[np.ndarray]) -> np.ndarray:
    """Concatenate mono float32 arrays (assumes same sample rate)."""
    if not parts:
        return np.zeros(0, dtype=np.float32)
    return np.concatenate(parts).astype(np.float32)


# --------------------- One-stop preprocessing ------------------ #

def preprocess_for_tts(
    wav_bytes: bytes,
    target_sr: int = 16000,
    trim: bool = True,
    denoise: bool = True,
    norm_dbfs: float = -20.0,
) -> Tuple[np.ndarray, int]:
    """
    Load bytes -> mono 16k -> (optional) trim + denoise -> normalize RMS.
    Returns (audio, sr).
    """
    x, sr = load_wav_bytes(wav_bytes)
    x, sr = to_mono_16k(x, sr) if target_sr == 16000 else (_linear_resample(x, sr, target_sr), target_sr)
    if trim:
        x = trim_silence(x, sr, thresh_db=-40.0, head_sec=0.25, tail_sec=0.3)
    if denoise:
        x = light_denoise(x, sr)
    x = normalize_rms(x, target_dbfs=norm_dbfs, limit_dbfs=-1.0)
    return x, sr
