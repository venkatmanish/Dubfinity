# backend/pipeline/audio_dub_pipeline.py
from __future__ import annotations
from typing import List, Dict, Optional, Tuple
import logging

from backend.agents.transcriber_agent import TranscriberAgent
from backend.agents.translator_agent import TranslatorAgent
from backend.agents.voice_style_agent import VoiceStyleAgent
from backend.agents.dubbing_agent import DubbingAgent
from backend.agents.quality_agent import QualityAgent
from backend.agents.orchestrator_agent import OrchestratorAgent
from backend.config import settings

logger = logging.getLogger(__name__)
cfg = settings()


class AudioDubPipeline:
    """
    Audio-only pipeline:
      1) ASR on Hindi input → segments with timestamps (placeholder diarization)
      2) Translate segments to target lang (await Atoms via SmallestClient with fallback)
      3) Extract simple prosody hints
      4) TTS per segment (voice selection via actor/voice_id) → concat WAV
      5) Optional QA
    """

    def __init__(
        self,
        asr: TranscriberAgent,
        translator: TranslatorAgent,
        style: VoiceStyleAgent,
        dubber: DubbingAgent,
        qa: Optional[QualityAgent] = None,
        orchestrator: Optional[OrchestratorAgent] = None,
    ):
        self.asr = asr
        self.translator = translator
        self.style = style
        self.dubber = dubber
        self.qa = qa or QualityAgent()
        self.orchestrator = orchestrator or OrchestratorAgent()

    async def process(
        self,
        wav_bytes: bytes,
        target_lang: str = "te",
        speaker_hint: Optional[str] = None,
        # accepted for future expansion; ignored by current dubber
        speaker_to_actor: Optional[Dict[str, str]] = None,  # noqa: ARG002
        preserve_timing: bool = True,                       # noqa: FBT001,ARG002
        watermark: Optional[bool] = None,                   # noqa: ARG002
        enforce_quality: bool = False,
        qa_audio_paths: Optional[Tuple[str, str]] = None,   # (orig_path, dubbed_path) for future audio-WER
        **kwargs,                                           # tolerate extras from callers
    ) -> bytes:
        """
        Run the full audio→audio dubbing pipeline and return a WAV byte stream.
        """
        _ = (speaker_to_actor, preserve_timing, watermark, kwargs)  # silence linters for now

        source_default = cfg.languages.get("source_default", "hi")

        # 1) ASR → segments (start/end/text/speaker)
        segments_hi: List[Dict] = self.asr.transcribe_segments(wav_bytes, src_lang=source_default)
        if not segments_hi:
            logger.info("AudioDubPipeline: ASR produced no segments; returning empty WAV.")
            return b""

        # 2) Translate (async)
        segments_tgt: List[Dict] = await self.translator.translate(
            segments_hi, target_lang=target_lang
        )

        # 3) Prosody extraction (lightweight)
        prosody_cfg = self.style.estimate(segments_tgt)

        # 4) Synthesize per segment and stitch
        dubbed_wav: bytes = self.dubber.synthesize_and_concat(
            segments=segments_tgt,
            prosody=prosody_cfg,
            speaker_hint=speaker_hint,
            lang=target_lang,
        )

        # 5) QA (stubbed)
        if enforce_quality:
            try:
                qa_text = self.qa.score_segments(segments_hi, segments_tgt)
                logger.info("QA(text) -> %s", qa_text)
                if qa_audio_paths:
                    # future hook for audio-ASR WER if you persist files
                    pass
            except Exception as e:
                logger.warning("QA step failed: %s", e)

        return dubbed_wav
