# Architecture Overview

TV Home 2.0 is a local client/server app that turns an old Linux PC into a
Google TV–style living-room box, replacing the v1 Flex Launcher prototype
(`base-version/`) with a proper UI and a backend that owns all system access.
See `docs/PRD.pdf` for the full product spec this implements.

## 1. Project structure

```
[repo root]/
├── frontend/             Preact + TypeScript + Vite shell UI
│   ├── src/
│   │   ├── focus/        In-house spatial-navigation engine (arrow keys → DOM geometry)
│   │   ├── state/        @preact/signals app state: server data (data.ts), UI/overlay
│   │   │                 state (ui.ts), and the nav controller tying both to the focus
│   │   │                 engine's scope stack (nav.ts)
│   │   ├── components/   Shared widgets: TopBar, AppBanner, QuickSettings, the
│   │   │                 on-screen keyboard, dialogs, toasts, screensaver
│   │   ├── settings/     One file per Settings-shell category (Wi-Fi, Bluetooth,
│   │   │                 Sound, Display, Date/time, Wallpaper, About, Power)
│   │   ├── screens/      Home, the Apps tab, the App Store, the Settings shell
│   │   └── styles/       Design tokens (colour/type scale) + component CSS
│   └── tests/e2e/        Playwright: screenshots + arrow-key reachability
├── backend/              Python 3, FastAPI + uvicorn
│   └── tv_home/
│       ├── apps.py, chrome.py       App install/launch/close (ported from v1)
│       ├── mock/                    Fake Wi-Fi/Bluetooth/Sound/Display/Power —
│       │                            used when TV_HOME_MOCK=1, so the whole app
│       │                            runs on a laptop with no real hardware
│       ├── system/                  Real integrations: dbus-fast (NetworkManager,
│       │                            BlueZ, logind), wpctl (sound), xrandr (display).
│       │                            Linux-only; see backend/README.md
│       ├── routes/                  One FastAPI router per API area
│       └── providers.py             Picks mock vs. real per module at import time
│   └── tests/                       pytest against the mock providers
├── session/              OS glue that makes the backend+UI *be* the desktop
│                         session on the real PC: LightDM autologin, global
│                         hotkeys (xbindkeys), a systemd watchdog, the
│                         installer/uninstaller. Linux-only; unverified outside
│                         the real Xubuntu box (see session/README.md)
├── base-version/         v1 prototype (Flex Launcher-based), kept for reference
└── docs/                 This file, the PRD, and other project docs
```

## 2. How the pieces talk to each other

```
[Remote / keyboard] → [Frontend: Preact UI, Chrome kiosk window]
                            │  REST (fetch) + WebSocket (/api/events)
                            ▼
                     [Backend: FastAPI, one local process]
                            │
          ┌─────────────────┼───────────────────────┐
          ▼                 ▼                        ▼
   apps.py/chrome.py   system/*.py (real)      mock/*.py (dev)
   (installed apps,    dbus-fast → NetworkManager/   in-memory fakes,
   kiosk Chrome         BlueZ/logind; wpctl; xrandr   no real hardware
   launch/close)        — real Linux box only         needed
```

The frontend never knows whether it's talking to `mock/` or `system/` — both
implement the same JSON shapes (see `frontend/src/types.ts`), selected once in
`backend/tv_home/providers.py` based on `TV_HOME_MOCK`.

## 3. Frontend

**Purpose:** the TV Home shell — Home screen, Apps tab, App Store, Settings,
on-screen keyboard — navigable with arrow keys/Enter/Back/Home only (a remote,
or a keyboard standing in for one during development).

**Technologies:** Preact, TypeScript, Vite, `@preact/signals` for state,
Playwright for e2e tests.

**Focus engine (`src/focus/`):** every on-screen control registers its DOM
element; arrow keys pick the nearest neighbour in that direction by comparing
edge gaps (the same heuristic behind CSS spatial navigation), weighted to
prefer same-row/column neighbours over diagonal ones. A scope stack
(`pushScope`/`popScope`) means opening a panel narrows what's reachable and
Back always restores focus to whatever opened it — see `focus/engine.ts`.

**Deployment:** served as static files by the backend in production (one
Chrome kiosk window pointed at `http://127.0.0.1:8000/`); served by Vite with
an API proxy in development.

## 4. Backend

**Purpose:** the only process with real system access — installed apps,
Wi-Fi, Bluetooth, sound, display, power — exposed over a small REST +
WebSocket API the frontend consumes.

**Technologies:** Python 3, FastAPI, uvicorn, dbus-fast (Linux only).

**Mock mode (`TV_HOME_MOCK=1`):** every system integration has a fake
in-memory counterpart under `mock/`, so the backend (and therefore the whole
UI) runs on any OS with no real Wi-Fi/Bluetooth/PipeWire/X11 present — this is
how the project was developed and tested outside the target Xubuntu PC.

**Deployment:** one `uvicorn` process, supervised by systemd on the real PC
(see `session/`), serving both the API and the built frontend.

## 5. Session (OS integration)

LightDM autologin → a custom X11 session (`tv-home-session.sh`): starts
`xfwm4` (compositor on — required for this hardware's GPU), the backend, and
a Chrome kiosk window pointed at the backend's own URL. `xbindkeysrc` grabs
Home/volume/recovery keys globally so they work over a running app. A systemd
unit restarts the backend on crash, falling back to the regular desktop after
repeated failures. `install.sh`/`uninstall.sh` set all of this up and back out.

This layer only runs on Linux and has not been exercised end-to-end outside
the real PC — see `session/README.md` for what to verify there.

## 6. Data stores

No database. Two small JSON files under `~/.config/tv-home/` on the real PC
(`apps.json`, `settings.json`), written atomically (write-to-temp-then-rename)
to survive a power loss mid-write. Icons are cached alongside them.

## 7. Testing

- Frontend: `npm run test:e2e` (Playwright) — covers Home/Apps navigation,
  Quick Settings, and the arrow-key-only reachability the PRD requires.
- Backend: `pytest` — app install/remove/launch logic and every mock provider's
  API contract.
- Both run against mock data; nothing in `backend/tv_home/system/` or
  `session/` is exercised by either suite (see the top-level README).

## 8. Known gaps / not yet built

- `common/` and `scripts/` (from the initial scaffold) are currently empty —
  nothing in this project needed a shared frontend/backend package or a
  separate automation script outside `session/`'s own installer.
- The 4 open questions from the PRD (project name, licence, multi-resolution/
  Wayland scope, reference remote) are answered with defaults in the PRD doc
  itself, not re-litigated here.
