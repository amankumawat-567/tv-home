# Changelog

All notable changes to TV Home are documented here. Versions correspond to
GitHub release tags; each release's tarball is built and attached
automatically by `.github/workflows/release.yml`.

## [2.0.2]

Fixes from a bug report filed after actually installing on the target
Xubuntu 26.04 PC, plus autologin automation and an app-aware screen-off
timer that had landed on `main` since 2.0.1 without a release. See
`docs/TODO.md`'s "Fixed from real-hardware testing" for the full detail.

### Fixed

- Installing from a downloaded release tarball (any folder name) required
  node/npm and then crashed — `install.sh` only skipped the frontend build
  behind an explicit `--from-release` flag, which a plain extract-and-run
  never passes. Now auto-detected from what's actually on disk.
- A stock Xubuntu autologin config (`lightdm.conf.d/50-autologin.conf`,
  pointing at the regular `xubuntu` session) silently won over TV Home's own.
  TV Home's config moved to `90-tv-home.conf` (loads after any such default)
  and the installer now scans for and reports conflicts before asking.
- The Settings → Display screen-off timer could blank the screen mid-movie
  (it had no idea an app was running). Launching an app now inhibits it;
  Home re-arms it. The setting also now survives a backend restart.

### Added

- `./session/install.sh --check` — a status command: installed path/version,
  session file presence, every autologin line found, the systemd service's
  status, backend reachability. Installs or changes nothing.
- `install.sh` now offers to enable autologin interactively on a fresh
  install, instead of leaving it as a manual doc step (skipped on updates,
  non-interactive runs, or a machine with no LightDM).

## [2.0.1]

### Added

- A starter wallpaper pack (`wallpapers/`) — 8 real photos, originally from
  Unsplash, tinted to match the UI's dark palette. `session/install.sh` now
  seeds them on a fresh install (never overwriting wallpapers you've already
  added).

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
