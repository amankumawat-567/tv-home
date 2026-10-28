# Contributing to TV Home

TV Home is a small, single-maintainer project (a home theater PC's launcher),
not a large open-source community — so this guide is short on process and
long on "how do I actually run this thing."

## Project layout

See `docs/ARCHITECTURE.md` for the full picture. The short version:

- `frontend/` — Preact + TypeScript + Vite UI.
- `backend/` — FastAPI service, with a mock mode for every system integration
  (Wi-Fi, Bluetooth, Sound, Display, Power) so the whole app runs on any OS.
- `session/` — Linux-only OS glue (LightDM, systemd, global hotkeys);
  unrunnable outside the real PC.
- `base-version/` — the retired v1 prototype, kept for reference only. Don't
  add new features there.

## Setting up

You need `node`/`npm` and `python3` — nothing else, since mock mode stands in
for the real Wi-Fi/Bluetooth/Sound/Display hardware.

```sh
# backend, in one terminal
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
TV_HOME_MOCK=1 uvicorn tv_home.main:app --reload --port 8000

# frontend, in another
cd frontend
npm install
npm run dev
```

Or `make dev` from the repo root runs both together — see `../Makefile`.

## Before opening a PR (or just committing to `main`)

```sh
make test   # backend pytest + frontend Playwright
make lint   # frontend type-check + backend syntax check
make build  # frontend production build
```

All three should pass. If you touched anything under `backend/tv_home/system/`
or `session/`, say so explicitly in the PR/commit — none of that is exercised
by the test suite (it needs the real Linux hardware; see each file's own
header comment and `session/README.md`), so it's reviewed by reading, not by
a green check mark.

## Conventions

- **Frontend:** function components + hooks, no class components. Global
  state lives in `@preact/signals` under `src/state/`, split into
  server-synced data (`data.ts`), ephemeral UI state (`ui.ts`), and the nav
  controller that ties overlays to the focus engine's scope stack (`nav.ts`).
  A new interactive element always goes through `useFocusable` — don't attach
  raw `:focus`/`onFocus` handling, the TV never gives elements real DOM focus.
- **Backend:** one module per concern (`apps.py`, `chrome.py`, `clock.py`,
  …), one FastAPI router per API area under `routes/`. A new system
  integration gets both a `mock/<name>.py` (so it's testable without
  hardware) and, if it needs real Linux access, a `system/<name>.py`, wired
  together in `providers.py`.
- **Comments:** explain *why*, not *what* — especially anything that looks
  unusual because it's working around specific hardware (the Intel GPU's
  compositor requirement, Chrome rewriting its own process title, etc.). A
  few of these are called out already; add to them rather than removing the
  context when you touch that code.

## Commit messages

Short imperative subject line, body explains *why* when it's not obvious from
the diff. Reference the PRD section a change implements when there is one
(e.g. "per the PRD's key map table").

## Reporting bugs / suggesting features

This is small enough that a GitHub issue with what you expected, what
happened instead, and (for a bug) the exact steps is plenty — no template
needed. If it's specific to the real hardware (the Pentium G620 box), say so;
most of this project's non-UI code can't be tested anywhere else.
