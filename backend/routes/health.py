from __future__ import annotations
import platform
from pathlib import Path
from typing import Dict, Any
from fastapi import APIRouter

try:
    from backend.config import settings
    cfg = settings()
except Exception:
    cfg = None

router = APIRouter()

def _safe_cfg(defaults: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(defaults)
    if not cfg:
        return out
    try:
        out["env"] = getattr(cfg, "ENV", out["env"])
        out["targets"] = getattr(cfg, "languages", {}).get("targets", out["targets"])
        out["audio_only"] = getattr(cfg, "output", {}).get("audio_only", out["audio_only"])
        out["otel_enabled"] = getattr(cfg, "telemetry", {}).get("otel_enabled", False)
        out["latency_ms_target"] = getattr(cfg, "thresholds", {}).get("latency_ms_target", out["latency_ms_target"])
    except Exception:
        pass
    return out

@router.get("/health", tags=["meta"])
def health():
    """
    Liveness/readiness with a few environment checks.
    Safe to call from k8s/Compose probes and Grafana.
    """
    voice_ids_path = (
        str(getattr(cfg, "VOICE_IDS_PATH", "demos/demo_assets/voice_ids.json"))
        if cfg else "demos/demo_assets/voice_ids.json"
    )
    voice_file = Path(voice_ids_path)
    has_voices = voice_file.exists()
    api_key_set = bool(getattr(cfg, "SMALLEST_API_KEY", "")) if cfg else False

    defaults = dict(
        env="dev",
        audio_only=True,
        targets=["te", "en", "kn"],
        otel_enabled=False,
        latency_ms_target=450,
    )
    meta = _safe_cfg(defaults)

    return {
        "ok": True,
        "service": "dubfinity-backend",
        "env": meta["env"],
        "platform": {
            "python": platform.python_version(),
            "system": platform.system(),
            "machine": platform.machine(),
        },
        "api_key_set": api_key_set,
        "voice_ids_path": voice_ids_path,
        "voice_ids_present": has_voices,
        "audio_only": meta["audio_only"],
        "targets": meta["targets"],
        "otel_enabled": meta["otel_enabled"],
        "latency_ms_target": meta["latency_ms_target"],
    }
