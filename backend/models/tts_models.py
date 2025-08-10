from __future__ import annotations
# FIX: import Literal from typing, not pydantic
from typing import Optional, Literal
from pydantic import BaseModel, Field, model_validator

class TTSRequest(BaseModel):
    text: str = Field(..., description="Text to convert to speech")
    actor: Optional[str] = Field(None, description="Actor key from voice_ids.json")
    voice_id: Optional[str] = Field(None, description="Direct Smallest voice ID (overrides actor if set)")
    language: Optional[str] = Field(None, description="Language code (e.g. 'te','en','kn','hi')")
    format: Literal["wav", "mp3"] = Field("wav", description="Output audio format")
    speed: Optional[float] = Field(1.0, ge=0.5, le=2.0, description="Speech speed multiplier")
    emotion: Optional[str] = Field(None, description="Optional emotion tag")
    enhancement: Optional[bool] = Field(None, description="Optional enhancement toggle")

    @model_validator(mode="after")
    def _require_voice(self):
        if not (self.actor or self.voice_id):
            raise ValueError("Provide either actor or voice_id")
        return self

class TTSResponse(BaseModel):
    audio_url: Optional[str] = Field(None, description="URL or path to the generated audio file")
    audio_base64: Optional[str] = Field(None, description="Base64-encoded audio data (optional)")
    duration_sec: Optional[float] = Field(None, description="Duration of generated audio (approx)")
