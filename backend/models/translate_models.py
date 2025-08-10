from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Literal, Union, List, Optional

class TranslateRequest(BaseModel):
    # Accept a single string or an array (matches OpenAPI + clients)
    text: Union[str, List[str]] = Field(..., description="Input text or array of texts")
    source_lang: Literal["auto", "en", "hi", "te", "kn"] = Field("auto", description="Source language")
    target_lang: Literal["en", "hi", "te", "kn"] = Field(..., description="Target language")

class TranslateResponse(BaseModel):
    # Mirror input shape: single string in, single string out; list in, list out
    translated_text: Union[str, List[str]] = Field(..., description="Translated output")
    detected_lang: Optional[str] = Field(None, description="Detected source language if source_lang=auto")
