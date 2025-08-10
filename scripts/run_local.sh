#!/usr/bin/env bash
# Convenience runner for dev:
# - starts backend with uvicorn
# - (optional) starts frontend vite dev server

set -euo pipefail

# If you use conda, uncomment:
# source "$(conda info --base)/etc/profile.d/conda.sh"
# conda activate smallest.ai

# Or venv:
if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

export PORT="${PORT:-8000}"
export ENV="${ENV:-dev}"

echo "[run] backend on :$PORT"
uvicorn backend.app:app --host 0.0.0.0 --port "$PORT" --reload &
BEPID=$!

if [ "${WITH_FRONTEND:-1}" = "1" ] && [ -d "frontend/web" ]; then
  echo "[run] frontend vite on :5173"
  (cd frontend/web && npm i && npm run dev) &
  FEPID=$!
else
  FEPID=""
fi

echo "[run] press Ctrl+C to stop"
trap 'echo; echo "[stop]"; kill -TERM $BEPID >/dev/null 2>&1; [ -n "$FEPID" ] && kill -TERM $FEPID >/dev/null 2>&1; wait || true; exit 0' INT TERM

wait
