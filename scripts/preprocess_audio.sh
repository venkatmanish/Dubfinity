#!/usr/bin/env bash
# Normalize your raw clips to mono/16k with gentle dynamic normalization.
# Usage:
#   scripts/preprocess_audio.sh dataset/train
#   scripts/preprocess_audio.sh dataset/test/scenes_hi

set -euo pipefail

ROOT="${1:-dataset/train}"

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg not found. Install via: brew install ffmpeg"; exit 1
fi

find "$ROOT" -type f \( -iname "*.wav" -o -iname "*.mp3" -o -iname "*.m4a" \) | while read -r f; do
  dir="$(dirname "$f")"
  base="$(basename "$f")"
  out="${dir}/${base%.*}_clean.wav"
  echo "[ffmpeg] $f -> $out"
  ffmpeg -hide_banner -loglevel error -y -i "$f" \
    -ac 1 -ar 16000 -af "highpass=f=80, dynaudnorm=p=1.0:s=5" "$out"
done

echo "[done] processed under $ROOT"
