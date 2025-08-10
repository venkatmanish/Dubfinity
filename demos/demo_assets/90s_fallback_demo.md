# Dubfinity — 90-second fallback (no internet / no keys)

**What still works offline**

- `/v1/voices` (reads local JSON)
- `/v1/tts` returns a **dummy WAV** if SDK/key missing (non-blocking)
- `/v1/dub-audio` can still run pipeline and stitch dummy audio segments

**Script (≈90 sec)**

1. “No internet? No problem. We designed for graceful degradation.”
2. Show `/v1/voices` in UI — IDs from `voice_ids.json`.
3. Hit **Synthesize**: explains _this is a placeholder tone_ (header `X-Debug: dummy-tts`).
4. Upload Hindi WAV → **dubbed.wav** plays tones stitched per segment.
5. “With keys restored, the same paths switch to real Smallest.ai voices instantly.”
