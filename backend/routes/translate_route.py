# backend/routes/translate_route.py

from __future__ import annotations
import logging
from typing import List, Union
from fastapi import APIRouter, HTTPException, Body

from backend.config import settings
from backend.models.translate_models import TranslateRequest, TranslateResponse
from backend.services.smallest_service import SmallestClient
from backend.agents.translator_agent import TranslatorAgent

router = APIRouter()
logger = logging.getLogger(__name__)
cfg = settings()

# Initialize shared service clients
_sdk = SmallestClient()
_translator = TranslatorAgent(
    client=_sdk,
    source_lang=cfg.languages.get("source_default", "hi"),
)

# Allowed target languages (union of config + defaults)
_ALLOWED = set(cfg.languages.get("targets", ["te", "en", "kn"]) + ["hi", "en", "kn", "te"])


@router.post(
    "/v1/translate",
    response_model=TranslateResponse,
    summary="Translate text using Smallest.ai",
)
async def translate(body: TranslateRequest = Body(...)):
    """
    Translates a string or list of strings from the configured source language
    into the requested target language using Smallest.ai atoms via TranslatorAgent.
    Falls back to original text if translation fails and fallback is enabled.
    """
    tgt = body.target_lang
    if tgt not in _ALLOWED:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported target_lang '{tgt}'"
        )

    try:
        # Handle list of strings
        if isinstance(body.text, list):
            results: List[str] = []
            for t in body.text:
                t = (t or "").strip()
                if t:
                    translated = await _translator.translate_text(t, tgt)
                    results.append(translated)
                else:
                    results.append(t)  # keep empty string
            return TranslateResponse(
                translated_text=results,
                detected_lang=(
                    body.source_lang
                    if body.source_lang != "auto"
                    else _translator.source_lang
                )
            )

        # Handle single string
        else:
            txt = (body.text or "").strip()
            translated = await _translator.translate_text(txt, tgt) if txt else txt
            return TranslateResponse(
                translated_text=translated,
                detected_lang=(
                    body.source_lang
                    if body.source_lang != "auto"
                    else _translator.source_lang
                )
            )

    except HTTPException:
        # Already a clean API error
        raise
    except Exception as e:
        logger.exception("Translation failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Translation failed: {e}"
        )
