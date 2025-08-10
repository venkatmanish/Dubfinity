import numpy as np
import io, wave
from backend.pipeline.audio_dub_pipeline import AudioDubPipeline
from backend.agents.transcriber_agent import TranscriberAgent
from backend.agents.translator_agent import TranslatorAgent
from backend.agents.voice_style_agent import VoiceStyleAgent
from backend.agents.dubbing_agent import DubbingAgent
from backend.agents.quality_agent import QualityAgent
from backend.agents.orchestrator_agent import OrchestratorAgent
from backend.services.smallest_service import SmallestClient

def _sine_wav_bytes(freq=440.0, seconds=1.0, sr=16000) -> bytes:
    t = np.linspace(0, seconds, int(sr*seconds), endpoint=False)
    x = 0.1 * np.sin(2*np.pi*freq*t).astype(np.float32)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
        wf.writeframes((x * 32767).astype("<i2").tobytes())
    return buf.getvalue()

def test_audio_pipeline_returns_bytes(monkeypatch):
    # Build agents/pipeline with a stub Smallest synth (avoids hitting network)
    sdk = SmallestClient(api_key=None)

    def fake_synthesize(text: str, voice_id: str, lang: str = "te") -> bytes:
        # create short tone per call; varies with text length
        dur = 0.3 + min(0.7, 0.02 * len(text or "x"))
        return _sine_wav_bytes(seconds=dur)

    monkeypatch.setattr(sdk, "synthesize", fake_synthesize, raising=True)

    asr = TranscriberAgent(src_lang="hi")
    tr = TranslatorAgent(client=sdk, source_lang="hi")
    style = VoiceStyleAgent()
    dub = DubbingAgent(sdk=sdk)
    qa = QualityAgent()
    orc = OrchestratorAgent()

    pipe = AudioDubPipeline(asr=asr, translator=tr, style=style, dubber=dub, qa=qa, orchestrator=orc)

    # Input "Hindi" audio can be any speech-like; we just use a dummy sine here
    input_wav = _sine_wav_bytes(seconds=1.2)
    out = pipe.process(input_wav, target_lang="te", speaker_hint=None)
    assert isinstance(out, (bytes, bytearray))
    # Must look like a WAV file: "RIFF" header
    assert out[:4] == b"RIFF"
