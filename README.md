Dubfinity — AI Audio Dubbing (Smallest.ai + LBTF)
Real-time, multi-speaker audio dubbing that routes across Smallest.ai speech services with LBTF’s intelligent model-switching for the best mix of latency, quality, and cost. Comes with a plug-and-play web UI, REST + WS APIs, metrics, and cloud-ready deploys.

What you get (at a glance)
ASR → Translate → TTS pipeline with per-segment timestamps

Multi-speaker mapping (speaker diarization labels → cloned voices)

Real-time WS TTS (token→speech streaming)

Voice remix controls (pitch/speed/emotion hooks)

LBTF Orchestrator that auto-picks fast vs. quality models based on latency budget

Prometheus metrics (+ ready-to-import Grafana dashboard)

Production-friendly layout (FastAPI backend + React/Vite frontend)

Architecture
bash
Copy
Edit
backend/
  agents/
    orchestrator_agent.py    # LBTF model switching (latency/quality budget)
    transcriber_agent.py     # ASR (+timestamps)
    translator_agent.py      # Smallest/atoms -> fallback translate
    voice_style_agent.py     # prosody extraction -> TTS params
    dubbing_agent.py         # per-segment TTS + stitch
    quality_agent.py         # QA hooks (WER stub + room to expand)
  pipeline/
    audio_dub_pipeline.py    # ASR -> translate -> TTS -> concat
    real_time_audio_pipeline.py
    multi_speaker_audio_pipeline.py
  routes/
    health.py                # /health
    voices.py                # /v1/voices
    translate.py             # /v1/translate
    tts.py                   # /v1/tts (REST) + /ws/tts (WebSocket)
    dub_audio.py             # /v1/dub-audio (file -> dubbed WAV)
  services/
    smallest_service.py      # Smallest.ai client (Waves/Atoms) + graceful fallbacks
    storage_service.py       # local/S3 abstraction
    safety_service.py        # content/watermark toggles
    subtitle_service.py      # SRT helpers (optional)
  models/                    # Pydantic schemas (tts/translate/dub)
  metrics/
    metrics_collector.py     # Prometheus counters/histograms
    prometheus_exports.py    # /metrics endpoint
  app.py                     # FastAPI app wiring & singletons
frontend/web/
  src/App.jsx                # Demo UI (controls, upload-dub, WS TTS, metrics)
  src/api/apiClient.js       # REST/WS helpers (proxy -> backend)
  vite.config.js             # dev proxy (/v1, /ws -> 127.0.0.1:8000)
demos/demo_assets/
  voice_ids.json             # your 5 pre-cloned voices (actor -> voice_id)
LBTF Orchestrator (where it lives):

backend/agents/orchestrator_agent.py decides between e.g. "lightning" and "lightning-large" TTS models and sets chunk sizes / speed knobs based on latency target and text length.

Used by routes/tts.py (REST/WS) and by pipeline/audio_dub_pipeline.py via the shared singletons in backend/app.py.

Prerequisites
OS: macOS or Linux (Windows WSL works)

Python: 3.10.x (recommended)

Node: 18+ (Node 20+ ideal)

ffmpeg: installed (for audio ops)

Ports: 8000 (backend) and 5173 (frontend) free

Install ffmpeg quickly:

bash
Copy
Edit
# macOS
brew install ffmpeg

# Debian/Ubuntu
sudo apt-get update && sudo apt-get install -y ffmpeg
1) Clone & create environment
bash
Copy
Edit
git clone <your-repo-url> dubfinity-ai
cd dubfinity-ai

# Option A: conda
conda create -n smallest.ai python=3.10 -y
conda activate smallest.ai

# Option B: venv
python3.10 -m venv .venv
source .venv/bin/activate
2) Backend install & config
Install Python deps
bash
Copy
Edit
pip install --upgrade pip
pip install -r requirements.txt
requirements.txt pins FastAPI, Uvicorn, Pydantic v2, NumPy, SoundFile, Prometheus client, OpenTelemetry (optional), and Smallest.ai client.

Create .env
Copy and edit:

bash
Copy
Edit
cp .env.example .env
Fill the important ones:

dotenv
Copy
Edit
# Smallest.ai
SMALLEST_API_KEY=sk-...               # your Smallest.ai key
SMALLEST_API_URL=https://waves-api.smallest.ai
SMALLEST_TRANSLATE_ATOM_ID=atom_...   # if you have an Atoms translator

# Voice map (actor -> voice_id)
VOICE_IDS_PATH=demos/demo_assets/voice_ids.json

# Telemetry (optional)
OTEL_ENABLED=false

# App
ENV=dev
Seed your voices
Open demos/demo_assets/voice_ids.json and put your cloned voices:

json
Copy
Edit
{
  "Sharmila": "voice_xxxxxx1",
  "AamirKhan": "voice_xxxxxx2",
  "AliaBhatt": "voice_xxxxxx3",
  "NarendraModi": "voice_xxxxxx4",
  "AkshayKumar": "voice_xxxxxx5"
}
3) Run the backend
bash
Copy
Edit
uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
You should see:

nginx
Copy
Edit
Uvicorn running on http://127.0.0.1:8000
Application startup complete.
Quick health checks
bash
Copy
Edit
curl http://127.0.0.1:8000/health
# → {"ok":true,"service":"dubfinity-backend","env":"dev", ...}

curl http://127.0.0.1:8000/v1/voices
# → [{"actor":"Sharmila","voice_id":"voice_xxxxxx1"}, ...]
TTS smoke test (saves a WAV)
bash
Copy
Edit
curl -X POST http://127.0.0.1:8000/v1/tts \
  -H "Content-Type: application/json" \
  -d '{"text":"नमस्ते! यह डेमो है।","actor":"Sharmila","language":"te","format":"wav"}' \
  -o /tmp/tts.wav -v
# play /tmp/tts.wav with your player
Dub audio smoke test (file → dubbed WAV)
bash
Copy
Edit
curl -X POST http://127.0.0.1:8000/v1/dub-audio \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/Hindi.wav" \
  -F "target_lang=te" \
  -F "actor=Sharmila" \
  -o /tmp/dubbed.wav
The /v1/dub-audio route runs the full pipeline: ASR → translate → per-segment TTS → stitch.

4) Frontend (React + Vite)
bash
Copy
Edit
cd frontend/web
npm install
The dev server is pre-wired to proxy API + WS:

frontend/web/vite.config.js

js
Copy
Edit
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/v1": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
      "/ws": { target: "ws://127.0.0.1:8000", ws: true }
    }
  }
});
Run it:

bash
Copy
Edit
npm run dev
Open http://localhost:5173 and try:

Controls → Synthesize (text→speech using your selected voice & language)

Upload & Dub (drop a Hindi WAV → dubbed output)

Real-time WS TTS (type and click “Speak” for streamed audio)

Multi-speaker Mapping (assign diarized speakers to specific voices)

5) How to call the APIs (developers)
Minimal fetch (Node/Browser)
js
Copy
Edit
// TTS
const res = await fetch("/v1/tts", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ text: "Hello world", actor: "Sharmila", language: "en" })
});
const wav = await res.arrayBuffer(); // play/save

// Dub (multipart)
const form = new FormData();
form.append("file", file);           // File from <input type="file" />
form.append("target_lang", "te");
form.append("actor", "AamirKhan");
const out = await fetch("/v1/dub-audio", { method: "POST", body: form });
const dubbed = await out.arrayBuffer();
WebSocket streaming
js
Copy
Edit
const ws = new WebSocket("ws://127.0.0.1:8000/ws/tts?actor=Sharmila&language=te");
ws.binaryType = "arraybuffer";

ws.onopen = () => ws.send(JSON.stringify({ text: "Streaming demo!" }));
ws.onmessage = (e) => {
  if (typeof e.data !== "string") {
    // e.data is audio/wav bytes; append to SourceBuffer or play via MediaSource
  } else {
    const msg = JSON.parse(e.data);
    if (msg.event === "done") ws.close();
  }
};
6) Where LBTF model-switching happens
backend/agents/orchestrator_agent.py:
Decides tts_model, chunk size, and speed based on latency budget and text length.

Used by

backend/routes/tts.py (both /v1/tts and /ws/tts)

backend/pipeline/audio_dub_pipeline.py (via injected singleton in app.py)

This lets Dubfinity automatically favor “lightning” for realtime and long text, and “lightning-large” for short text where quality matters — all without the caller needing to care.

7) Metrics / Observability
Prometheus counters + histograms in backend/metrics/metrics_collector.py

Exported at /metrics (scrape with Prometheus)

Prebuilt Grafana dashboard in metrics/grafana_dashboard.json

Prometheus scrape example:

yaml
Copy
Edit
scrape_configs:
  - job_name: 'dubfinity'
    static_configs:
      - targets: ['127.0.0.1:8000']
8) Testing
bash
Copy
Edit
pytest -q
# tests/*
Smoke tests include:

test_endpoints_smoke.py

test_audio_pipeline.py

test_latency_agent.py

9) Docker & Cloud (optional)
Docker Compose
bash
Copy
Edit
docker compose -f cloud_deploy/docker-compose.yml up --build
# backend on 8000, frontend on 5173 (adjust compose if needed)
Helm (GKE/EKS)
Charts under cloud_deploy/helm/

Tweak values.yaml for env vars + secrets

Ingress sample shipped for a managed LB

10) Advanced configuration
Languages: set defaults in backend/config/settings.py (e.g., source "hi"; targets ["te","en","kn"])

Watermarking: backend/services/safety_service.py toggles/flags

Storage: swap local_store.py ↔ s3_store.py via StorageService

Prosody hooks: processing/prosody.py and VoiceStyleAgent

Subtitle generation: subtitle_service.py for SRT from timestamps

11) Troubleshooting (fast)
Port in use

bash
Copy
Edit
# macOS
lsof -i :8000
kill -9 <pid>
Frontend says “proxy error /v1/…”
Make sure backend is on 127.0.0.1:8000 and Vite proxy matches (not 0.0.0.0).

No voices listed
Confirm VOICE_IDS_PATH points to a real JSON and the file exists.

Audio plays 0:00
Most browsers require a user gesture before playing audio; click “Synthesize” then hit play.
Also ensure the <audio> has a valid src created from Blob([bytes], {type:"audio/wav"}).

Mic / WS TTS errors
Allow microphone permissions in the browser and ensure websockets aren’t blocked by a corporate proxy.

12) USP
Production-minded: Clean separation of agents, pipelines, and routes.

Cloud-ready: Helm charts + metrics out of the box.

Extensible: Swap translators, TTS providers, storage backends easily.

Developer-first: Minimal APIs, working demo UI, Postman collection in api/.

13) Live demo script (3 minutes)
Open the UI (http://localhost:5173).
“This is Dubfinity — real-time AI dubbing built on Smallest.ai with LBTF model switching to stay under a 450 ms budget.”

Synthesize text in Hindi, switch language to Telugu, play.
“The orchestrator picks lightning-large for short text to maximize quality.”

Upload & Dub a short Hindi clip.
“We run ASR → translate → per-segment TTS and preserve pacing. You can map diarized speakers to cloned voices.”

Real-time WS TTS: type and click Speak.
“Tokens stream to the server; Smallest.ai Waves streams audio back. Latency stays under budget thanks to LBTF.”

Metrics: hit /metrics or show Grafana.
“Every request is observable — latency histograms, p50/p95, and model choice.”

Close: “Plug-and-play APIs, cloud-ready, and built for creators and platforms who want global reach, in their own voice.”

License
MIT — see LICENSE.

