#!/usr/bin/env bash
# Installs a few catalog apps via a running backend's own API, so Home isn't
# empty right after a fresh `make dev` — purely a convenience for local
# demoing/screenshots, not something the app needs at runtime (the real App
# Store flow is how apps normally get added).
set -euo pipefail

BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8000}"
APPS=(netflix youtube spotify)

if ! curl -fs -o /dev/null "$BACKEND_URL/api/state"; then
  echo "No backend reachable at $BACKEND_URL — run \`make dev\` first." >&2
  exit 1
fi

for id in "${APPS[@]}"; do
  echo "==> Installing $id"
  curl -fs -X POST "$BACKEND_URL/api/apps" \
    -H 'Content-Type: application/json' \
    -d "{\"id\":\"$id\",\"name\":\"$id\",\"url\":\"\"}" \
    -o /dev/null
done

echo "==> Done — refresh the frontend to see them on Home."
