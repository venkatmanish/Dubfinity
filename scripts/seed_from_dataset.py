#!/usr/bin/env python3
"""
Seed pre-cloned voices from dataset/train/<ActorName>/*.wav using Smallest Waves REST.
- Respects clone quota: stops on "clone limit exceeded"
- Writes/updates demos/demo_assets/voice_ids.json
"""
from __future__ import annotations
import os, json, time
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "dataset" / "train"
OUT = ROOT / "demos" / "demo_assets" / "voice_ids.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

API_KEY = os.getenv("SMALLEST_API_KEY")
if not API_KEY:
    raise SystemExit("Set SMALLEST_API_KEY in env first")

# REST endpoint used earlier in your logs
ADD_VOICE_URL = "https://waves-api.smallest.ai/api/v1/lightning-large/add_voice"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

# Load existing map if any (won’t overwrite existing actors)
mapping = {}
if OUT.exists():
    try:
        mapping = json.loads(OUT.read_text())
    except Exception:
        pass

def try_add(actor: str, wav_path: Path) -> str | None:
    with wav_path.open("rb") as f:
        files = {"file": (wav_path.name, f, "audio/wav")}
        data = {"name": actor}
        r = requests.post(ADD_VOICE_URL, headers=HEADERS, files=files, data=data, timeout=120)
    if r.status_code == 200:
        js = r.json()
        # expected shape seen earlier:
        # {"message":"Voice clone created successfully","data":{"voiceId":"voice_...","model":"lightning-large","status":"completed"}}
        vid = (js.get("data") or {}).get("voiceId")
        return vid
    # Explicit quota error sample we saw:
    if r.status_code == 400 and "clone limit exceeded" in r.text:
        print(f"[quota] {actor}: {r.text.strip()}")
        return None
    raise RuntimeError(f"{r.status_code} {r.text}")

def main():
    created = 0
    for actor_dir in sorted([d for d in DATASET.iterdir() if d.is_dir()]):
        actor = actor_dir.name
        if actor in mapping:
            print(f"[skip] {actor} already mapped -> {mapping[actor]}")
            continue
        wavs = sorted(list(actor_dir.glob("*_trim.wav")) or list(actor_dir.glob("*_clean.wav")) or list(actor_dir.glob("*.wav")))
        if not wavs:
            print(f"[skip] no wavs for {actor}")
            continue

        for w in wavs:
            try:
                print(f"[upload] {actor} -> {w.name}")
                vid = try_add(actor, w)
                if vid:
                    mapping[actor] = vid
                    print(f"[ok] {actor} -> {vid}")
                    created += 1
                    break
                else:
                    # quota hit
                    break
            except Exception as e:
                print(f"[retry] {actor} with {w.name}: {e}")
                time.sleep(1.0)
                continue

    OUT.write_text(json.dumps(mapping, indent=2), encoding="utf-8")
    print(f"[done] Saved mapping: {OUT}")
    print(f"[summary] total={len(mapping)} newly_created={created}")

if __name__ == "__main__":
    main()
