# TV Home 2.0

Turns an old Linux PC into a living-room box that looks and works like Google TV,
set up and used with a remote (or a keyboard standing in for one) alone.

- `frontend/` — the shell UI: Preact + TypeScript + Vite, running full-screen in a
  Chrome kiosk window.
- `backend/` — a local FastAPI service that owns all system access (apps, Wi-Fi,
  Bluetooth, sound, display, power) and pushes live state to the UI over a
  WebSocket.
- `session/` — the OS glue that makes the backend+UI *be* the desktop session on
  the target PC (LightDM autologin, global hotkeys, a systemd watchdog, and the
  installer/uninstaller). These only run on the real Xubuntu box.
- `base-version/` — the v1 prototype (`tv-home.py`/`tv-store.py`, Flex
  Launcher-based), kept for reference; superseded by everything above.
- `docs/` — the PRD and project documentation.

See `frontend/README.md` and `backend/README.md` for how to run each piece in
development (both support a mock mode with no real Wi-Fi/Bluetooth/Sound
hardware, so the whole UI runs on a laptop). `session/README.md` covers
installing onto the real PC.
