from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from backend.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)
cfg = settings()

def _voice_map_path() -> Path:
    return Path(getattr(cfg, "VOICE_IDS_PATH", "demos/demo_assets/voice_ids.json"))

def _load_voice_map() -> dict[str, str]:
    p = _voice_map_path()
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"{p} not found")
    try:
        return json.loads(p.read_text())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"failed to read mapping: {e}")

@router.get("/v1/voices", summary="List available voices (actor → voice_id)")
def list_voices(actor: Optional[str] = Query(None, description="Optional actor name to filter")):
    """
    Returns an array of {actor, voice_id}. If `actor` is provided, returns only that entry.
    """
    data = _load_voice_map()
    if actor:
        if actor not in data:
            raise HTTPException(status_code=404, detail=f"actor '{actor}' not found")
        return [{"actor": actor, "voice_id": data[actor]}]
    return [{"actor": k, "voice_id": v} for k, v in sorted(data.items())]
