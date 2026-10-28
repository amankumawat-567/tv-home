# Changelog

All notable changes to TV Home are documented here. Versions correspond to
GitHub release tags; each release's tarball is built and attached
automatically by `.github/workflows/release.yml`.

## [2.0.0] — full rewrite

Replaces the v1 Flex Launcher prototype (`base-version/`) with a proper
client/server app: a Preact/TypeScript frontend and a FastAPI backend that
owns all system access, following `docs/PRD.pdf`.

### Added

- Home screen, Apps tab, and App Store, all navigable by arrow keys/Enter/
  Back/Home alone, via an in-house spatial-navigation focus engine.
- Quick Settings and a full Settings shell: Wi-Fi, Bluetooth, Sound, Display,
  Date/time, Wallpaper, About, Power.
- An on-screen QWERTY keyboard used by every text field (Wi-Fi passwords,
  adding a website to the App Store).
- A mock mode (`TV_HOME_MOCK=1`) for every system integration, so the whole
  app runs on any OS with no real Wi-Fi/Bluetooth/PipeWire/X11 present.
- OS session integration for the real PC: LightDM autologin, global hotkeys,
  a systemd-supervised backend with a crash-count fallback to the desktop,
  and an installer/uninstaller.
- Self-update from GitHub Releases (Settings → About → "Update to …").
- A test suite (pytest + Playwright) and CI that runs it on every push.

### Known gaps

See `docs/TODO.md` for what's built-but-unverified (anything needing the
real Linux hardware) vs. not built yet (first-run wizard, phone-typing via
QR, remote key remapping).
