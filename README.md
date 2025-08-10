# dubfinity-ai (audio-only, Smallest.ai hackathon)

Multilingual **audio dubbing** for Hindi → **Telugu / English / Kannada** using
Smallest.ai (Waves + Atoms). Audio in → transcription → translation → per-segment
TTS with **pre-cloned voices** → stitched WAV out. Includes real-time WS TTS and
LLM→speech streaming (optional).

## Quickstart

### 1) Environment

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env with your key(s)
```
