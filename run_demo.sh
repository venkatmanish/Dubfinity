#!/usr/bin/env bash
set -euo pipefail

# ----------------------------
# Dubfinity AI Backend Runner
# ----------------------------

# Change to script directory
cd "$(dirname "$0")"

# Optional: load .env if present
if [ -f ".env" ]; then
  echo "[INFO] Loading .env..."
  export $(grep -v '^#' .env | xargs)
fi

# Python environment check
if ! command -v python3 >/dev/null 2>&1; then
  echo "[ERROR] Python3 is not installed."
  exit 1
fi

# # Install dependencies if needed
# if [ ! -d "venv" ]; then
#   echo "[INFO] Creating virtual environment..."
#   python3 -m venv venv
# fi

# echo "[INFO] Activating virtual environment..."
# source venv/bin/activate

# Install requirements
if [ -f "requirements.txt" ]; then
  echo "[INFO] Installing dependencies..."
  pip install --upgrade pip
  pip install -r requirements.txt
else
  echo "[WARN] requirements.txt not found, skipping pip install."
fi

# Default port and host
HOST=${HOST:-0.0.0.0}
PORT=${PORT:-8000}

# Run backend with auto-reload
echo "[INFO] Starting Dubfinity AI Backend on ${HOST}:${PORT}..."
exec uvicorn backend.app:app --reload --host "$HOST" --port "$PORT"

