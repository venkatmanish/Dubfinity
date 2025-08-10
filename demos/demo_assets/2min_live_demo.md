# Dubfinity — 2-minute live demo (audio-only)

**Setup**

- Backend running at `http://localhost:8000`
- Frontend running with `npm run dev`
- `demos/demo_assets/voice_ids.json` present (5 voices)

**Script (≈120 seconds)**

1. **Intro (0:00–0:20)**

   - “We built an audio-only Hindi → Telugu/English/Kannada dubbing system on Smallest.ai.”
   - “It uses pre-cloned voices (Aamir, Akshay, Alia, Narendra, Salman).”

2. **List voices (0:20–0:30)**

   - In frontend, refresh voices panel. (Shows the 5 actors.)
   - “These IDs are fetched from a mapping; no cloning at demo time.”

3. **TTS single line (0:30–0:55)**

   - Choose **Telugu** + **AamirKhan**.
   - Paste: `नमस्ते! आज हम डबिंग का जादू दिखाने वाले हैं।`
   - Click **Synthesize** → play audio.
   - “Low latency TTS via Smallest Waves.”

4. **Upload Hindi audio → dubbed audio (0:55–1:30)**

   - Upload a short Hindi WAV (`dataset/test/scenes_hi/scene_01.wav`).
   - Target: **Kannada**; Speaker: **AliaBhatt**.
   - Play the returned **dubbed.wav**.
   - “Pipeline: ASR → translate (Atoms stub/future) → per-segment TTS → concat.”

5. **WS TTS stream (1:30–1:50)**

   - In **Real-time WS TTS**, click **Speak** with default prompt.
   - “We can stream incremental audio; token-to-speech path is wired for later.”

6. **Close (1:50–2:00)**
   - “Ship-ready API, partner clients, Prometheus hooks, and clean deploy.”
   - “Happy to integrate this widget into Smallest.ai product UI.”

**Backup plan**

- If network/API key missing, our endpoints return **dummy WAV** tones (so demo never stalls).
