from __future__ import annotations
# FIX: import Literal from typing, not pydantic
from typing import Optional, List, Dict, Literal
from pydantic import BaseModel, Field, HttpUrl, model_validator

class Segment(BaseModel):
    start: float = Field(..., ge=0.0, description="Start time (seconds)")
    end: float = Field(..., ge=0.0, description="End time (seconds)")
    text: str = Field("", description="Transcript (source or translated)")
    speaker: Optional[str] = Field(None, description="Diarization label, e.g., spk1")
    voice_id: Optional[str] = Field(None, description="Override voice for this segment")
    src_lang: Optional[str] = Field(None, description="Source language code")
    tgt_lang: Optional[str] = Field(None, description="Target language code")

    @model_validator(mode="after")
    def _end_after_start(self):
        if self.end < self.start:
            raise ValueError("end must be >= start")
        return self

class DubRequest(BaseModel):
    audio_url: Optional[HttpUrl] = Field(None, description="URL of source audio")
    audio_base64: Optional[str] = Field(None, description="Base64-encoded source audio")
    audio_path: Optional[str] = Field(None, description="Local filesystem path (internal use)")
    segments: Optional[List[Segment]] = Field(None, description="Optional precomputed segments")

    source_lang: Optional[str] = Field("hi", description="Source language code (default hi)")
    target_lang: str = Field(..., description="Target language code: te | en | kn")

    actor: Optional[str] = Field(None, description="Actor key from voice_ids.json")
    speaker_to_actor: Optional[Dict[str, str]] = Field(
        None, description='Map diarized speakers to actors, e.g. {"spk1":"AamirKhan","spk2":"AliaBhatt"}'
    )

    output_format: Literal["wav", "mp3"] = Field("wav", description="Output audio format")
    preserve_timing: bool = Field(True, description="Insert silences to preserve original pacing")
    watermark: Optional[bool] = Field(None, description="Override global watermark toggle")

    @model_validator(mode="after")
    def _one_input_required(self):
        if not (self.audio_url or self.audio_base64 or self.audio_path or self.segments):
            raise ValueError("Provide one of: audio_url | audio_base64 | audio_path | segments")
        return self

class DubResponse(BaseModel):
    dubbed_audio_url: Optional[str] = Field(None, description="URL/path of dubbed audio")
    dubbed_audio_base64: Optional[str] = Field(None, description="Base64-encoded dubbed audio (optional)")
    segments: Optional[List[Segment]] = Field(None, description="Segments after translation (for inspection)")
    duration_sec: Optional[float] = Field(None, description="Approx duration of dubbed audio")
    qa: Optional[Dict] = Field(None, description="QA metrics (e.g., WER)")
