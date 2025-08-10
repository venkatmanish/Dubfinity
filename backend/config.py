from __future__ import annotations
import os
from pathlib import Path
from typing import Any, Dict
import yaml
from pydantic import BaseModel
from dotenv import load_dotenv

# Load .env early
load_dotenv()

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config.yaml"

def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

class Settings(BaseModel):
    # Env
    ENV: str = os.getenv("ENV", "dev")
    PORT: int = int(os.getenv("PORT", "8000"))
    SMALLEST_API_KEY: str | None = os.getenv("SMALLEST_API_KEY")
    GROQ_API_KEY: str | None = os.getenv("GROQ_API_KEY")

    # Paths
    ROOT: Path = ROOT
    VOICE_IDS_PATH: Path = ROOT / "demos" / "demo_assets" / "voice_ids.json"
    TMP_DIR: Path = ROOT / ".tmp"

    # YAML-driven knobs (with sensible defaults)
    modes: Dict[str, Any] = {}
    languages: Dict[str, Any] = {}
    flows: Dict[str, Any] = {}
    thresholds: Dict[str, Any] = {}
    output: Dict[str, Any] = {}
    storage: Dict[str, Any] = {}
    telemetry: Dict[str, Any] = {}

def load_settings() -> Settings:
    data = _load_yaml(CONFIG_PATH)
    s = Settings(
        modes=data.get("modes", {}),
        languages=data.get("languages", {}),
        flows=data.get("flows", {}),
        thresholds=data.get("thresholds", {}),
        output=data.get("output", {}),
        storage=data.get("storage", {}),
        telemetry=data.get("telemetry", {}),
    )
    s.TMP_DIR.mkdir(parents=True, exist_ok=True)
    return s

# Singleton-style accessor
_settings: Settings | None = None
def settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings
