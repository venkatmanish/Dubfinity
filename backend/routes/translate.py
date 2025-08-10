# backend/api/routes/translate.py
from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Literal

from backend.services.smallest_service import SmallestClient
from backend.agents.translator_agent import TranslatorAgent, TranslatorAgentConfig

router = APIRouter()
logger = logging.getLogger(__name__)

class TranslateRequest(BaseModel):
    text: str = Field(..., description="Input text to translate")
    source_lang: Literal["auto", "hi", "en", "te", "kn"] = Field("auto")
    target_lang: Literal["hi", "en", "te", "kn"]

class TranslateResponse(BaseModel):
    translated_text: str
    detected_lang: str

# Initialize translator agent (Hindi default; we override per request)
_client = SmallestClient()
_agent = TranslatorAgent(
    client=_client,
    source_lang="hi",
    config=TranslatorAgentConfig(source_lang="hi", allow_passthrough_fallback=True)
)

@router.post("/v1/translate", response_model=TranslateResponse)
async def translate_endpoint(req: TranslateRequest):
    try:
        # update source language dynamically for this call
        _agent.source_lang = req.source_lang
        out = await _agent.translate(req.text, req.target_lang)
        if not isinstance(out, str):
            raise ValueError("Unexpected translation output shape")
        return TranslateResponse(translated_text=out, detected_lang=req.source_lang)
    except Exception as e:
        logger.exception("translate failed: %s", e)
        raise HTTPException(status_code=500, detail=f"translate failed: {e}")
