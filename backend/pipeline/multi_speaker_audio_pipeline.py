from __future__ import annotations
from typing import Dict, Optional, List
import logging

from backend.agents.transcriber_agent import TranscriberAgent
from backend.agents.translator_agent import TranslatorAgent
from backend.agents.voice_style_agent import VoiceStyleAgent
from backend.agents.dubbing_agent import DubbingAgent
from backend.services.storage_service import StorageService
from backend.config import settings

logger = logging.getLogger(__name__)
cfg = settings()


class MultiSpeakerAudioPipeline:
    """
    ASR → diarization → translation → per-speaker TTS (multi-voice) → stitch → store.
    """

    def __init__(
        self,
        transcriber: TranscriberAgent,
        translator: TranslatorAgent,
        voice_style: VoiceStyleAgent,
        dubbing: DubbingAgent,
        storage: StorageService,
    ):
        self.transcriber = transcriber
        self.translator = translator
        self.voice_style = voice_style
        self.dubbing = dubbing
        self.storage = storage

    def run(
        self,
        audio_path: str,
        target_lang: str,
        speaker_to_actor: Optional[Dict[str, str]] = None,
        preserve_timing: bool = True,
        watermark: Optional[bool] = None,
    ) -> str:
        logger.info("MultiSpeaker: %s → %s", audio_path, target_lang)

        # 1) ASR + diarization (placeholder labels spk1/spk2…)
        segments: List[Dict] = self.transcriber.transcribe_with_diarization(audio_path)
        if not segments:
            raise RuntimeError("ASR produced no segments")

        # 2) Translation (segment-wise)
        for seg in segments:
            txt = seg.get("text", "") or ""
            if txt:
                seg["text"] = self.translator.translate_text(txt, target_lang)
            seg["tgt_lang"] = target_lang

        # 3) Prosody
        prosody_map = self.voice_style.extract_prosody(segments)

        # 4) TTS per speaker with mapping + timing/watermark controls
        dubbed_wav = self.dubbing.synthesize_and_concat(
            segments=segments,
            prosody=prosody_map,
            speaker_to_actor=speaker_to_actor,
            lang=target_lang,
            preserve_timing=preserve_timing,
            watermark=watermark,
        )

        # 5) Store & return URL/path
        output_path = self.storage.save_bytes(dubbed_wav, suffix=".wav")
        logger.info("MultiSpeaker: saved %s", output_path)
        return output_path
