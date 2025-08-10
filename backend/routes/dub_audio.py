# backend/routes/dub_audio.py
from __future__ import annotations

import json
import logging
from typing import Optional, Dict

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import Response

# Use the singleton pipeline created in backend/app.py
from backend.app import audio_pipeline
from backend.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()
cfg = settings()


@router.post("/v1/dub-audio", summary="Hindi audio → dubbed audio (WAV bytes)")
async def dub_audio(
    file: UploadFile = File(..., description="Source audio (WAV/MP3/M4A; WAV preferred)"),
    target_lang: str = Form(..., description="Target language code: te | en | kn"),
    actor: Optional[str] = Form(None, description="Actor key (from voice_ids.json) used as a hint"),
    # Accepted for future expansion; validated but not yet applied in pipeline
    speaker_to_actor: Optional[str] = Form(
        None,
        description='JSON mapping like {"spk1":"AamirKhan","spk2":"AliaBhatt"} (ignored for now)',
    ),
    preserve_timing: bool = Form(True, description="Keep inter-segment gaps (ignored for now)"),
    watermark: Optional[bool] = Form(None, description="Override watermark (ignored for now)"),
    output_format: str = Form("wav", description="wav | mp3 (currently always returns WAV)"),
):
    """
    Dubs the uploaded Hindi audio into the selected target language using pre-cloned voices.
    Returns raw WAV bytes so the frontend can play with `audio.src = URL.createObjectURL(blob)`.
    """
    try:
        # ——— Basic validation ———
        allowed_targets = set(cfg.languages.get("targets", ["te", "en", "kn"]))
        if target_lang not in allowed_targets:
            raise HTTPException(status_code=400, detail=f"Unsupported target_lang '{target_lang}'")

        wav_bytes = await file.read()
        if not wav_bytes:
            raise HTTPException(status_code=400, detail="Empty file")

        # Validate mapping JSON if provided (even though we ignore it for now)
        if speaker_to_actor:
            try:
                parsed: Dict[str, str] = json.loads(speaker_to_actor)
                if not isinstance(parsed, dict):
                    raise ValueError("speaker_to_actor must be a JSON object")
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid speaker_to_actor JSON: {e}")

        # ——— Run pipeline (ASR → translate → TTS → stitch) ———
        # NOTE: pipeline.process is async — we MUST await it.
        dubbed_wav: bytes = await audio_pipeline.process(
            wav_bytes=wav_bytes,
            target_lang=target_lang,
            speaker_hint=actor or None,
            enforce_quality=False,
            # We accept these in the signature for forward-compat; no-ops for now:
            speaker_to_actor=None,
            preserve_timing=preserve_timing,
            watermark=watermark,
        )

        if not dubbed_wav:
            raise HTTPException(status_code=500, detail="Pipeline returned empty audio")

        # ——— Respond (WAV) ———
        headers = {
            "Content-Disposition": 'attachment; filename="dub.wav"',
            "X-Synthetic-Audio": "dubfinity-smallest",
        }
        return Response(content=dubbed_wav, media_type="audio/wav", headers=headers)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("dub-audio failed: %s", e)
        raise HTTPException(status_code=500, detail=f"dub-audio failed: {e}")
