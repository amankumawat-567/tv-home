# Changelog

All notable changes to TV Home are documented here. Versions correspond to
GitHub release tags; each release's tarball is built and attached
automatically by `.github/workflows/release.yml`.

## [2.1.2]

Fixes the real bug behind 2.1.1's reported symptom: `install.sh` and
`install.sh --check` could die completely silently — no error, no prompt,
just back at the shell — on a perfectly normal, unmodified Xubuntu install.

### Fixed

- **`set -e`/`pipefail` + "grep found nothing" silently killed the script.**
  `install.sh` scans each LightDM config file for an existing
  `autologin-user`/`autologin-session` line; on a stock system most of those
  files (starting with `/etc/lightdm/lightdm.conf` itself, checked first)
  have no such line at all, which is the normal, expected case — but under
  `set -euo pipefail`, assigning a `grep | tail | cut` pipeline's output to a
  variable aborts the entire script the instant grep finds no match, with no
  error message. This hit two separate spots: `run_doctor()`'s own loop (so
  `--check` died right after printing the "Autologin" header) and
  `configure_autologin()`'s call to `other_autologin_configs()` (so a real
  install died right after installing the polkit rule, before the autologin
  prompt — the real explanation for "the prompt never came up", not the
  `/dev/tty` issue 2.1.1 fixed, which was real but never actually reached).
  Fixed by treating "no match" as the expected non-error outcome (`|| true`)
  at every one of these spots. Reproduced locally with the exact stock
  `lightdm.conf` content reported against this bug, confirmed it now runs to
  completion. **Confirmed on the real PC**: the autologin prompt appeared,
  was answered, and the LightDM config was written — the first full
  end-to-end confirmation of this flow on real hardware.

## [2.1.1]

Fixes a real install on Xubuntu 26.04 that completed successfully but never
booted into TV Home: autologin was silently never configured.

### Fixed

- **The autologin prompt could silently never appear.** `configure_autologin`
  in `session/install.sh` checked `[ ! -t 0 ]` (is stdin a terminal) to decide
  whether to ask; stdin isn't always a tty even when a real terminal *is*
  attached (depends on exactly how the script gets invoked), so on at least
  one real machine the whole install ran to completion — including `sudo`
  prompts, which read from `/dev/tty` directly and so worked fine — but the
  `read -p` autologin prompt, which reads from stdin, never showed up and the
  install finished with autologin silently left off. Fixed: the prompt now
  reads from `/dev/tty` directly too, same as `sudo` already does, and only
  gives up when there's truly no controlling terminal at all (the case this
  guard exists for — the backend's own non-interactive self-update).

## [2.1.0]

Closes out the PRD's remaining backlog — the five items that were sitting in
`docs/TODO.md`'s "Not built yet". See "Added in 2.1.0" there for the detail
behind each.

### Added

- **First-run setup wizard (Y4)**: Welcome → Wi-Fi → Remote → Apps → Home,
  shown once per install, Home-key skippable at any step.
- **Phone-typing via QR code (I2)**: the on-screen keyboard can hand off to a
  phone — scan a QR code, type there, it appears live and auto-submits on
  Done.
- **Remote key remapping / learn mode (I3)**: Settings → Remote lets any of
  the 8 actions be rebound to a different key, with a reset-to-defaults
  option.
- **Wallpaper slideshow now persists**: the interval (5/15/30/60 min) and
  on/off state survive a backend restart and actually rotate wallpapers on a
  timer, instead of being a local-only UI toggle.
- **A real Material Symbols icon set**: hand-rolled stand-in icons replaced
  with real Apache-2.0 Material Symbols path data, bundled inline (no runtime
  network dependency). The Wi-Fi signal-bars icon stays hand-drawn on
  purpose — it renders live signal strength, which no static glyph can.

## [2.0.3]

Fixes "power features are not working like shutdown, go to desktop, restart
and sleep," reported against a detailed setup/boot requirements spec. See
`docs/TODO.md`'s "Fixed from real-hardware testing (2.0.3)" for the detail.

### Fixed

- **Go to desktop never worked**: it killed the backend process, but
  `tv-home-session.sh`'s loop is blocked waiting on the Chrome *window*, not
  the backend — so nothing ever caused it to proceed to the desktop handoff.
  Now closes TV Home's own shell window directly (`chrome.close_shell()`).
- **Sleep/restart/shut down likely failed on missing authorization**: these
  call logind over D-Bus, which requires polkit to explicitly allow the
  action without a password — nothing previously granted that. Added a
  polkit rule (`session/polkit/46-tv-home.rules.template`), installed with
  the real username substituted in on every install/update. Failures now
  report "Not allowed" specifically when authorization is the cause.

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
