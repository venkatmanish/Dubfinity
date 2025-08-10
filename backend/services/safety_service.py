from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple

@dataclass
class SafetyResult:
    allowed: bool
    reason: str = ""

PROFANITY = {"fuck", "shit", "bastard", "asshole"}  # toy list; replace with real policy

def basic_content_check(text: str) -> SafetyResult:
    """
    Minimal content check. Swap with a real policy model or service later.
    """
    t = (text or "").lower()
    if any(w in t for w in PROFANITY):
        return SafetyResult(False, "contains profanity")
    return SafetyResult(True, "")

def watermark_flags(enabled: bool) -> Tuple[bool, dict]:
    """
    Return (should_embed, params) to guide audio watermarking.
    Actual embedding should happen in audio_utils during concat.
    """
    if not enabled:
        return False, {}
    # Tunables for your watermark embedder (placeholder)
    return True, {"strength": 0.1, "freq": 18000}
