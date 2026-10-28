#!/usr/bin/env bash
# Type-checks the frontend and sanity-checks the backend compiles. No linter
# is configured yet (ruff/eslint aren't dependencies) — this is the minimum
# "does this actually parse/type-check" bar. See `make lint`.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
status=0

echo "==> Frontend: tsc --noEmit"
(cd "$REPO_ROOT/frontend" && npx tsc -b --noEmit) || status=1

echo
echo "==> Backend: syntax check"
if [ -d "$REPO_ROOT/backend/.venv" ]; then
  PY="$REPO_ROOT/backend/.venv/bin/python"
else
  PY="python3"
fi
(cd "$REPO_ROOT/backend" && "$PY" -m compileall -q tv_home tests) || status=1

if [ "$status" -eq 0 ]; then
  echo
  echo "==> All checks passed"
else
  echo
  echo "==> Some checks failed" >&2
fi
exit $status
