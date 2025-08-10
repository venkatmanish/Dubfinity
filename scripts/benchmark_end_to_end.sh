#!/usr/bin/env bash
# Quick latency + correctness smoke:
# - hits /v1/voices
# - runs /v1/tts
# - uploads a sample to /v1/dub-audio
# Prints basic timings; saves outputs to ./.tmp_bench

set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
ACTOR="${ACTOR:-AamirKhan}"
LANG="${LANG:-te}"
SCENE="${SCENE:-dataset/test/scenes_hi/scene_01.wav}"
OUTDIR=".tmp_bench"
mkdir -p "$OUTDIR"

echo "== Benchmark (BASE_URL=$BASE_URL, ACTOR=$ACTOR, LANG=$LANG) =="

echo "-- voices"
time curl -s "$BASE_URL/v1/voices" | tee "$OUTDIR/voices.json" >/dev/null

echo "-- tts"
time curl -s -X POST "$BASE_URL/v1/tts" \
  -H "Content-Type: application/json" \
  -d "{\"text\":\"नमस्ते, यह एक परीक्षण है।\",\"actor\":\"$ACTOR\",\"lang\":\"$LANG\"}" \
  --output "$OUTDIR/tts.wav"

echo "-- dub-audio ($SCENE)"
time curl -s -X POST "$BASE_URL/v1/dub-audio?target_lang=$LANG&actor=$ACTOR" \
  -F "file=@$SCENE" \
  --output "$OUTDIR/dub.wav"

ls -lh "$OUTDIR" || true
echo "[done] artifacts in $OUTDIR"
