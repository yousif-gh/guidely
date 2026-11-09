#!/usr/bin/env bash
# Runs backend (FastAPI) and frontend (Vite) together. Ctrl+C stops both.
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- backend setup ---
if [ ! -d "$ROOT_DIR/.venv" ]; then
  python3 -m venv "$ROOT_DIR/.venv"
fi
source "$ROOT_DIR/.venv/bin/activate"
pip install -q -r "$ROOT_DIR/requirements.txt"

if [ ! -f "$ROOT_DIR/.env" ]; then
  cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
fi

# --- frontend setup ---
if [ ! -d "$ROOT_DIR/frontend/node_modules" ]; then
  (cd "$ROOT_DIR/frontend" && npm install)
fi

cleanup() {
  echo "Stopping..."
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
}
trap cleanup EXIT INT TERM

(cd "$ROOT_DIR/backend" && uvicorn main:app --reload --port 8000) &
BACKEND_PID=$!

(cd "$ROOT_DIR/frontend" && npm run dev) &
FRONTEND_PID=$!

echo "Backend  -> http://localhost:8000"
echo "Frontend -> http://localhost:5173"

wait "$BACKEND_PID" "$FRONTEND_PID"
