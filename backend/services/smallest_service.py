from __future__ import annotations

import io
import os
import logging
import asyncio
import math
from typing import Iterable, Optional, AsyncIterable, Dict, List, Any, Union

import numpy as np

# optional libs
try:
    import aiohttp
except Exception:
    aiohttp = None

try:
    import requests
except Exception:
    requests = None

# official SDK (Waves)
try:
    from smallestai.waves import WavesClient, AsyncWavesClient  # type: ignore
except Exception:
    WavesClient = None  # type: ignore
    AsyncWavesClient = None  # type: ignore

# Google Translate (primary translator)
try:
    from deep_translator import GoogleTranslator  # type: ignore
except Exception:
    GoogleTranslator = None

# gTTS (speech fallback) + pydub to convert MP3→WAV
try:
    from gtts import gTTS  # type: ignore
except Exception:
    gTTS = None

try:
    from pydub import AudioSegment  # type: ignore
except Exception:
    AudioSegment = None

# local config
try:
    from backend.config import settings
    cfg = settings()
except Exception:
    cfg = None

logger = logging.getLogger(__name__)


# ---------------- Utilities ----------------
def _tone_wav(seconds: float = 1.0, sr: int = 16000, freq: float = 480.0, amp: float = 0.14) -> bytes:
    import wave
    seconds = max(0.35, float(seconds))
    t = np.linspace(0.0, seconds, int(sr * seconds), endpoint=False)

    fade = int(0.01 * sr)
    env = np.ones_like(t, dtype=np.float32)
    if 2 * fade < len(env):
        env[:fade] = np.linspace(0.0, 1.0, fade, dtype=np.float32)
        env[-fade:] = np.linspace(1.0, 0.0, fade, dtype=np.float32)

    tone = (amp * np.sin(2 * math.pi * freq * t) * env).astype(np.float32)
    pcm16 = (np.clip(tone, -1.0, 1.0) * 32767.0).astype("<i2")

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm16.tobytes())
    return buf.getvalue()


def _chunk_bytes(data: bytes, chunk: int = 1920) -> Iterable[bytes]:
    for i in range(0, len(data), chunk):
        yield data[i:i + chunk]


def _split_for_streaming(text: str, max_chars: int = 320) -> List[str]:
    import re
    text = (text or "").strip()
    if not text:
        return []
    parts = re.split(r"(?<=[\.\?\!।])\s+", text)
    chunks: List[str] = []
    buf = ""
    for p in parts:
        if not p:
            continue
        if len(buf) + (1 if buf else 0) + len(p) <= max_chars:
            buf = f"{buf} {p}".strip() if buf else p
        else:
            if buf:
                chunks.append(buf)
            if len(p) > max_chars:
                for i in range(0, len(p), max_chars):
                    chunks.append(p[i:i + max_chars])
                buf = ""
            else:
                buf = p
    if buf:
        chunks.append(buf)
    return chunks


async def _tiny_sleep():
    try:
        await asyncio.sleep(0.01)
    except Exception:
        pass


async def _aiter_bytes(data: bytes, chunk: int = 1920):
    for b in _chunk_bytes(data, chunk):
        yield b
        await _tiny_sleep()


# ---------------- Language maps ----------------
LANG_CODE_TO_NAME = {"hi": "Hindi", "te": "Telugu", "en": "English", "kn": "Kannada"}
LANG_NAME_TO_CODE = {v: k for k, v in LANG_CODE_TO_NAME.items()}

# gTTS code map (all four supported)
GTTS_LANG_MAP = {"en": "en", "hi": "hi", "te": "te", "kn": "kn"}


# ---------------- Client ----------------
class SmallestClient:
    """
    TTS: Smallest Waves first; fallback to gTTS MP3->WAV; final fallback tone.
    Translation: Google first; optional Atoms (if configured); fallback passthrough.
    """

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, timeout: int = 60):
        self.api_key = api_key or (getattr(cfg, "SMALLEST_API_KEY", None) if cfg else os.getenv("SMALLEST_API_KEY"))
        default_base = "https://waves-api.smallest.ai"
        self.base_url = base_url or (getattr(cfg, "SMALLEST_API_URL", None) if cfg else default_base) or default_base
        self.timeout = timeout

        self._waves: Optional[WavesClient] = None
        self._waves_async: Optional[AsyncWavesClient] = None

        if WavesClient and self.api_key:
            try:
                self._waves = WavesClient(api_key=self.api_key)
                logger.info("SmallestClient: WavesClient initialized.")
            except Exception as e:
                logger.warning("SmallestClient: WavesClient init failed: %s", e)

        if AsyncWavesClient and self.api_key:
            try:
                self._waves_async = AsyncWavesClient(api_key=self.api_key)
                logger.info("SmallestClient: AsyncWavesClient initialized.")
            except Exception as e:
                logger.warning("SmallestClient: AsyncWavesClient init failed: %s", e)

        self._requests: Optional[requests.Session] = None
        if requests:
            self._requests = requests.Session()
            if self.api_key:
                self._requests.headers.update({"Authorization": f"Bearer {self.api_key}"})

        self._aio_session: Optional[aiohttp.ClientSession] = None

    # ---------------- TTS ----------------
    @staticmethod
    def _pick_model_for_voice(voice_id: Optional[str]) -> str:
        return "lightning-large" if voice_id and voice_id.startswith("voice_") else "lightning"

    def synthesize(
        self,
        text: str,
        voice_id: str,
        lang: Optional[str] = None,
        model: Optional[str] = None,
        speed: Optional[float] = None,
        consistency: Optional[float] = None,
        similarity: Optional[float] = None,
        enhancement: Optional[bool] = None,
        sample_rate: int = 16000,
        add_wav_header: bool = True,
    ) -> bytes:
        if not text:
            return _tone_wav(0.25)

        # 1) Smallest Waves (correct call signature: text positional, rest kwargs)
        try:
            if self._waves:
                return self._waves.synthesize(
                    text,
                    voice_id=voice_id,
                    language=(lang or "en"),
                    model=(model or self._pick_model_for_voice(voice_id)),
                    speed=(speed if speed is not None else 1.0),
                    consistency=(consistency if consistency is not None else 0.5),
                    similarity=(similarity if similarity is not None else 0.0),
                    enhancement=bool(enhancement) if enhancement is not None else False,
                    sample_rate=sample_rate,
                    add_wav_header=add_wav_header,
                )
        except Exception as e:
            logger.error("Waves synth failed: %s", e)

        # 2) REST fallback (if exposed for your account)
        if self._requests:
            try:
                url = f"{self.base_url}/api/v1/lightning/get_speech"
                payload = {
                    "text": text,
                    "voice_id": voice_id,
                    "language": (lang or "en"),
                    "speed": speed or 1.0,
                    "consistency": 0.5 if consistency is None else consistency,
                    "similarity": 0.0 if similarity is None else similarity,
                    "enhancement": 1 if enhancement else 0,
                    "sample_rate": sample_rate,
                    "output_format": "wav",
                }
                resp = self._requests.post(url, json=payload, timeout=self.timeout)
                resp.raise_for_status()
                return resp.content
            except Exception as e:
                logger.debug("REST synth fallback failed: %s", e)

        # 3) gTTS fallback (real speech)
        if gTTS and AudioSegment:
            try:
                g_lang = GTTS_LANG_MAP.get((lang or "en"), "en")
                mp3_buf = io.BytesIO()
                gTTS(text=text, lang=g_lang, slow=False).write_to_fp(mp3_buf)
                mp3_buf.seek(0)
                audio = AudioSegment.from_file(mp3_buf, format="mp3")
                audio = audio.set_channels(1).set_frame_rate(16000).set_sample_width(2)
                wav_buf = io.BytesIO()
                audio.export(wav_buf, format="wav")
                return wav_buf.getvalue()
            except Exception as e:
                logger.error("gTTS fallback failed: %s", e)

        # 4) Audible tone as last resort
        dur = max(0.8, min(4.0, 0.6 + 0.015 * len(text)))
        return _tone_wav(dur, sr=16000, freq=480.0)

    async def stream_token_tts(
        self,
        prompt: Optional[str] = None,
        token: Optional[str] = None,
        is_final: bool = False,
        voice_id: Optional[str] = None,
        lang: Optional[str] = None,
        model: Optional[str] = None,
        speed: Optional[float] = None,
        enhancement: Optional[bool] = None,
        chunk: int = 1920,
    ) -> AsyncIterable[bytes]:
        text = (prompt or token or "").strip()
        if not text:
            async for b in _aiter_bytes(_tone_wav(0.5), chunk):
                yield b
            return

        for piece in _split_for_streaming(text, max_chars=200) or [text]:
            wav = self.synthesize(
                text=piece,
                voice_id=voice_id or "emily",
                lang=lang,
                model=model or (self._pick_model_for_voice(voice_id) if voice_id else None),
                speed=speed or 1.0,
                enhancement=enhancement,
            )
            async for b in _aiter_bytes(wav, chunk):
                yield b

    # ---------------- Translation ----------------
    async def translate_via_atoms(
        self,
        texts: Union[str, List[str]],
        source_lang: str = "auto",
        target_lang: str = "te",
    ) -> Union[str, List[str]]:
        input_was_str = isinstance(texts, str)
        items: List[str] = [texts] if input_was_str else list(texts or [])

        # 1) Google Translate first
        if GoogleTranslator:
            try:
                def _batch(inp: List[str], src: str, tgt: str) -> List[str]:
                    src_code = LANG_NAME_TO_CODE.get(src, src)
                    tgt_code = LANG_NAME_TO_CODE.get(tgt, tgt)
                    out: List[str] = []
                    for s in inp:
                        out.append("" if not s else GoogleTranslator(source=src_code, target=tgt_code).translate(s))
                    return out

                parsed = await asyncio.to_thread(_batch, items, source_lang, target_lang)
                return parsed[0] if input_was_str else parsed
            except Exception as e:
                logger.warning("GoogleTranslator failed, passthrough: %s", e)

        # 2) (Optional) Atoms REST — only if you configure SMALLEST_TRANSLATE_ATOM_ID
        atom_id = os.getenv("SMALLEST_TRANSLATE_ATOM_ID") or (getattr(cfg, "SMALLEST_TRANSLATE_ATOM_ID", None) if cfg else None)

        if atom_id and self.api_key:
            # aiohttp REST
            if aiohttp:
                try:
                    if not self._aio_session:
                        self._aio_session = aiohttp.ClientSession(headers={"Authorization": f"Bearer {self.api_key}"})
                    url = f"{self.base_url}/api/v1/atoms/{atom_id}/run"
                    payload = {"texts": items, "source_lang": source_lang, "target_lang": target_lang}
                    async with self._aio_session.post(url, json=payload, timeout=self.timeout) as resp:
                        resp.raise_for_status()
                        data = await resp.json()
                        parsed = self._parse_atom_response(data)
                        if parsed is not None:
                            return parsed[0] if input_was_str else parsed
                except Exception as e:
                    logger.debug("Atoms (aiohttp) translate failed: %s", e)

            # requests REST
            if self._requests:
                try:
                    url = f"{self.base_url}/api/v1/atoms/{atom_id}/run"
                    payload = {"texts": items, "source_lang": source_lang, "target_lang": target_lang}
                    resp = self._requests.post(url, json=payload, timeout=self.timeout)
                    resp.raise_for_status()
                    data = resp.json()
                    parsed = self._parse_atom_response(data)
                    if parsed is not None:
                        return parsed[0] if input_was_str else parsed
                except Exception as e:
                    logger.debug("Atoms (requests) translate failed: %s", e)

        # 3) Passthrough
        logger.warning("translate_via_atoms: falling back to passthrough.")
        return items[0] if input_was_str else items

    @staticmethod
    def _parse_atom_response(resp: Any) -> Optional[List[str]]:
        try:
            if isinstance(resp, dict):
                out = resp.get("output", resp)
                if isinstance(out, dict) and "translated_texts" in out:
                    vals = out["translated_texts"]
                    if isinstance(vals, list):
                        return [str(x) for x in vals]
                if isinstance(out, list):
                    return [str(x) for x in out]
            elif isinstance(resp, list):
                return [str(x) for x in resp]
        except Exception:
            pass
        return None

    # ---------------- Cleanup ----------------
    async def close_async(self):
        if self._aio_session:
            try:
                await self._aio_session.close()
            except Exception:
                pass
            self._aio_session = None

    def close(self):
        if self._requests:
            try:
                self._requests.close()
            except Exception:
                pass
            self._requests = None
