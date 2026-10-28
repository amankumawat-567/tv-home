#!/usr/bin/env bash
# Runs the full test suite: backend pytest (against the mock providers) and
# frontend Playwright (against the mock backend). See `make test`.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
status=0

echo "==> Backend: pytest"
if [ ! -d "$REPO_ROOT/backend/.venv" ]; then
  python3 -m venv "$REPO_ROOT/backend/.venv"
  "$REPO_ROOT/backend/.venv/bin/pip" install -q -e "$REPO_ROOT/backend[dev]"
fi
(cd "$REPO_ROOT/backend" && ".venv/bin/pytest" -q) || status=1

echo
echo "==> Frontend: Playwright e2e"
if [ ! -d "$REPO_ROOT/frontend/node_modules" ]; then
  (cd "$REPO_ROOT/frontend" && npm install)
fi
(cd "$REPO_ROOT/frontend" && npx playwright install --with-deps chromium >/dev/null 2>&1 || npx playwright install chromium) || true
(cd "$REPO_ROOT/frontend" && npx playwright test) || status=1

exit $status
