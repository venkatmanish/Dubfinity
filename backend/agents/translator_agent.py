# backend/agents/translator_agent.py
from __future__ import annotations
from typing import List, Dict, Optional, Union, Tuple
import logging
from dataclasses import dataclass

from backend.services.smallest_service import SmallestClient

logger = logging.getLogger(__name__)

LANG_CODE_TO_NAME = {
    "hi": "Hindi",
    "te": "Telugu",
    "en": "English",
    "kn": "Kannada",
}

@dataclass
class TranslatorAgentConfig:
    source_lang: str = "hi"
    allow_passthrough_fallback: bool = True
    max_cache: int = 2048


class TranslatorAgent:
    """
    Handles text translation using Smallest.ai via SmallestClient.

    - Caches translations to avoid duplicate calls
    - Can optionally fall back to original text if translation fails
    """

    def __init__(
        self,
        client: SmallestClient,
        source_lang: str = "hi",
        config: Optional[TranslatorAgentConfig] = None
    ):
        self.client = client
        self.cfg = config or TranslatorAgentConfig(source_lang=source_lang)
        self.source_lang = self.cfg.source_lang
        self._cache: Dict[Tuple[str, str, str], str] = {}

    # ---------------- Helper Methods ---------------- #

    def _lang_name(self, code: str) -> str:
        """Convert language code to full name for API calls."""
        return LANG_CODE_TO_NAME.get(code, code)

    def _cache_get(self, text: str, src: str, tgt: str) -> Optional[str]:
        """Retrieve cached translation if available."""
        return self._cache.get((text, src, tgt))

    def _cache_set(self, text: str, src: str, tgt: str, out: str) -> None:
        """Store translation in cache."""
        if len(self._cache) >= self.cfg.max_cache:
            try:
                self._cache.pop(next(iter(self._cache)))  # remove oldest-ish
            except Exception:
                self._cache.clear()
        self._cache[(text, src, tgt)] = out

    # ---------------- Core Translation Methods ---------------- #

    async def translate_text(self, text: str, target_lang: str) -> str:
        """
        Translate a single string asynchronously.
        Returns original text if translation fails and fallback is enabled.
        """
        if not text:
            return text

        src_name = self._lang_name(self.source_lang)
        tgt_name = self._lang_name(target_lang)

        # Cache
        cached = self._cache_get(text, src_name, tgt_name)
        if cached is not None:
            return cached

        try:
            # IMPORTANT: (texts, target_lang, source_lang)
            out = await self.client.translate_via_atoms(
                text,
                target_lang=tgt_name,
                source_lang=src_name,
            )
            if not isinstance(out, str) or not out.strip():
                raise ValueError(f"Invalid translation output: {out!r}")
            self._cache_set(text, src_name, tgt_name, out)
            return out
        except Exception as e:
            logger.warning(
                "TranslatorAgent: translation failed (%s→%s): %s",
                src_name, tgt_name, e
            )
            if self.cfg.allow_passthrough_fallback:
                return text
            raise

    async def translate_segments(self, segments: List[Dict], target_lang: str) -> List[Dict]:
        """
        Translate a list of segment dictionaries asynchronously.
        Each segment must contain a 'text' field.
        """
        out: List[Dict] = []
        for s in segments:
            txt = s.get("text", "") or ""
            translated = await self.translate_text(txt, target_lang) if txt else txt
            out.append({
                **s,
                "src_lang": self.source_lang,
                "tgt_lang": target_lang,
                "text": translated
            })
        return out

    async def translate(self, x: Union[str, List[Dict]], target_lang: str) -> Union[str, List[Dict]]:
        """
        Convenience method for translating either a string or list of segments.
        """
        if isinstance(x, str):
            return await self.translate_text(x, target_lang)
        return await self.translate_segments(x, target_lang)
