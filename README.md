# TV Home 2.0

[![CI](https://github.com/amankumawat-567/tv-home/actions/workflows/ci.yml/badge.svg)](https://github.com/amankumawat-567/tv-home/actions/workflows/ci.yml)
[![Latest release](https://img.shields.io/github/v/release/amankumawat-567/tv-home)](https://github.com/amankumawat-567/tv-home/releases/latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Turns an old Linux PC into a living-room box that looks and works like Google
TV, set up and used with a remote (or a keyboard standing in for one) alone.

## Install (on the Xubuntu PC)

No need to clone the repo or install Node.js — download the latest release,
which ships a prebuilt frontend:

```sh
curl -s https://api.github.com/repos/amankumawat-567/tv-home/releases/latest \
  | grep '"browser_download_url.*tar\.gz"' | cut -d '"' -f 4 \
  | xargs curl -sL -o tv-home.tar.gz
tar xzf tv-home.tar.gz && cd tv-home-*/
./session/install.sh
```

Or grab the tarball by hand from the
[releases page](https://github.com/amankumawat-567/tv-home/releases/latest),
extract it, and run `session/install.sh` from inside.

**Updating** afterwards doesn't need the command line: Settings → About shows
when a new version is available and installs it with one select (Y6). Or run
the installer again from a freshly downloaded release.

## Repo layout

- `frontend/` — the shell UI: Preact + TypeScript + Vite, running full-screen
  in a Chrome kiosk window.
- `backend/` — a local FastAPI service that owns all system access (apps,
  Wi-Fi, Bluetooth, sound, display, power, self-update) and pushes live state
  to the UI over a WebSocket.
- `session/` — the OS glue that makes the backend+UI *be* the desktop session
  on the target PC (LightDM autologin, global hotkeys, a systemd watchdog,
  and the installer/uninstaller). These only run on the real Xubuntu box.
- `base-version/` — the v1 prototype (`tv-home.py`/`tv-store.py`, Flex
  Launcher-based), kept for reference; superseded by everything above.
- `docs/` — the PRD, architecture/design docs, diagrams, and `TODO.md`.
- `wallpapers/` — a starter pack of 8 real photos (tinted to match the UI),
  seeded onto a fresh install by `session/install.sh`.
- `scripts/`, `makefile` — local dev convenience (`make dev`, `make test`, …).

## Developing

```sh
make dev   # backend (mock mode) + frontend dev server, together
make test  # backend pytest + frontend Playwright e2e
```

See `frontend/README.md`, `backend/README.md` and `docs/CONTRIBUTING.md` for
more. `session/README.md` covers installing onto the real PC in detail,
including what to verify since that part can't be tested anywhere else.
