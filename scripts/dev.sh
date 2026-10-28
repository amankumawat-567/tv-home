#!/usr/bin/env bash
# Runs the backend (mock mode) and the frontend dev server together, with
# everything torn down on Ctrl+C. Works on any OS — mock mode stands in for
# the real Wi-Fi/Bluetooth/Sound/Display hardware. See `make dev`.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$REPO_ROOT/backend"
FRONTEND_DIR="$REPO_ROOT/frontend"

if [ ! -d "$BACKEND_DIR/.venv" ]; then
  echo "==> Creating the backend virtualenv (first run only)"
  python3 -m venv "$BACKEND_DIR/.venv"
  "$BACKEND_DIR/.venv/bin/pip" install -q -e "$BACKEND_DIR[dev]"
fi
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  echo "==> Installing frontend dependencies (first run only)"
  (cd "$FRONTEND_DIR" && npm install)
fi

pids=()
cleanup() {
  echo
  echo "==> Stopping dev servers"
  for pid in "${pids[@]:-}"; do
    [ -n "$pid" ] && kill "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT INT TERM

echo "==> Backend (mock mode) on http://127.0.0.1:8000"
(cd "$BACKEND_DIR" && TV_HOME_MOCK=1 "$BACKEND_DIR/.venv/bin/uvicorn" tv_home.main:app --reload --port 8000) &
pids+=($!)

echo "==> Frontend on http://127.0.0.1:5173"
(cd "$FRONTEND_DIR" && npm run dev) &
pids+=($!)

wait
