# Changelog

All notable changes to TV Home are documented here. Versions correspond to
GitHub release tags; each release's tarball is built and attached
automatically by `.github/workflows/release.yml`.

## [2.2.4]

Found while debugging why 2.2.3's "Set up TV remote" button appeared not to
exist at all on the real PC, despite `VERSION` reading 2.2.3 — a much bigger
bug than the KDE Connect feature itself.

### Fixed

- **Updating never actually refreshed the kiosk screen.** `install.sh`
  restarted the backend service on update, but the already-running kiosk
  Chrome window has no reason to reload on its own — it just keeps showing
  whatever frontend bundle it loaded at its last page load, indefinitely.
  So the backend (and `VERSION`) would update correctly while the *visible
  UI* silently kept showing the old one, with nothing telling you this was
  happening — exactly how a confirmed-updated install could be missing an
  entire settings page. Fixed: `install.sh` now also closes the kiosk shell
  window after restarting the backend (the same mechanism "Go to desktop"
  uses to close it, minus the sentinel, so `tv-home-session.sh`'s loop
  relaunches it fresh instead of falling to the desktop) — covers both a
  manual `install.sh` re-run and the in-app Settings → About self-update,
  since both go through the same script.
- **Duplicate KDE Connect devices with identical names were
  indistinguishable in Settings → Remote connect.** Re-pairing a phone
  after reinstalling its KDE Connect app leaves a stale, no-longer-reachable
  entry behind with the exact same name as the live one — the UI showed
  "Paired" for both with no way to tell them apart, which is how "Set up TV
  remote" ended up getting pushed to a stale duplicate instead of the real
  connection. Fixed: paired devices now show "Paired — not nearby" when not
  currently reachable, duplicate names get a short ID suffix, and "Set up
  TV remote" is disabled on an unreachable entry entirely.

## [2.2.3]

Follow-up to 2.2.2's TV remote feature: a real pairing (done via a Mac
running the actual KDE Connect desktop app, confirmed on v2.2.2) showed no
Run Commands at all, confirming the suspected gap.

### Added

- **"Set up TV remote" for already-paired devices** (Settings → Remote
  connect). `pair()`/`accept()` only write the Run Command config at the
  exact moment pairing happens — a device paired before this feature
  existed, or paired through any path other than TV Home's own Settings
  page (e.g. accepted entirely from the other device's own KDE Connect
  app), never got it written at all, and there was previously no way to fix
  that short of unpairing and re-pairing. Every paired device now gets a
  "Set up TV remote" row that pushes the config on demand
  (`POST /api/kdeconnect/install-remote`,
  `system/kdeconnect.py`'s `install_remote()`) — safe to run any number of
  times. *Verified*: new backend test, and a manual Playwright pass showing
  the row, the action succeeding, and the confirmation toast.

## [2.2.2]

One fix and one feature, both found/requested right after trying KDE Connect
pairing for the first time.

### Fixed

- **`kdeconnectd` never actually started, so pairing never worked at all.**
  The `kdeconnect` package ships both a D-Bus service-activation file and an
  XDG autostart `.desktop` entry for its daemon — the latter needs a real
  desktop session manager (xfce4-session, gnome-session, …) to process
  autostart entries at all, which this minimal kiosk session never runs, and
  D-Bus activation alone wasn't reliably starting it either. Fixed:
  `tv-home-session.sh` now starts `kdeconnectd` directly, the same way it
  already does for `xbindkeys` (and kills it on "Go to desktop", for the
  same orphaned-background-job reason `xfwm4`/`xbindkeys` already needed
  that). `install.sh --check` now also reports whether `kdeconnectd` is
  actually running, not just whether the package is installed.
- **All wallpapers were invisible — the picker was just a blind "Next"
  button.** Settings → Wallpaper never listed what wallpapers existed or let
  you pick one directly; the only option cycled forward one at a time with
  no preview of what was coming. Separately, the preview/background image
  wouldn't reliably update after switching anyway — `/wallpaper` serves
  different content from the same URL depending on which one is selected,
  which browsers can cache past the point it's stale. Fixed: a real
  thumbnail gallery (`GET /api/wallpaper/list`, `GET /wallpaper/{index}`,
  `POST /api/wallpaper/set`) showing every wallpaper with the current one
  marked, direct tap-to-select, `Cache-Control: no-store` on the
  current-wallpaper endpoint, and a `wallpaperVersion` cache-busting token
  in app state so the Home screen's background reliably updates. Also
  fixed a real latent bug caught along the way: `config.WALL_DIRS` was a
  module-level list built once at import time from `USER_WALLS`, the exact
  "bound at import, breaks monkeypatch test isolation" gotcha this project
  already fixed for other config values — converted to a `wall_dirs()`
  function. Verified with a real Playwright pass against seeded wallpaper
  files (screenshots showing all 8 wallpapers, selection, and the Home
  background actually changing) and new backend tests.

### Added

- **A real TV-remote layout for KDE Connect, not just the generic
  trackpad.** Pairing now also writes the phone's KDE Connect "Run Command"
  plugin config with a ready-made D-pad (Up/Down/Left/Right/OK/Back/Home/
  Menu/volume) — each button runs `xdotool key <X>` using the same X11
  keysym names a real keyboard already sends, matched against
  `state/keymap.ts`'s defaults so these buttons go through the exact same
  key handling (including any remapping done in Settings → Remote), no
  separate input-handling code needed. The config file format
  (`~/.config/kdeconnect/<id>/kdeconnect_runcommand/config`, a Qt
  `QSettings` INI file) and exact escaping were taken from kdeconnect-kde's
  own source and verified by round-tripping a generated file through a real
  `QSettings` instance — not guessed. `install.sh` now also installs
  `xdotool`. *Unverified beyond that*: needs a real pairing on the real PC
  to confirm the phone's app actually shows the buttons.

## [2.2.1]

Fixes "Go to desktop" (and the Home key) taking up to ~90 seconds-2 minutes
instead of being instant, reported after the black-screen fix in 2.1.3.

### Fixed

- **Closing Chrome only ever sent SIGTERM, with nothing forcing it to
  actually die quickly.** `go_home()`/`close_shell()` sent SIGTERM and
  returned immediately, trusting Chrome to exit promptly — on this hardware
  (an old PC, possibly slow storage) a kiosk profile's cache/cookie/
  service-worker flush, or just one hung renderer, can leave the browser
  process alive for a long time after SIGTERM. That directly delayed
  `tv-home-session.sh`'s foreground wait on that exact process (for "Go to
  desktop") and, separately, `systemctl --user stop` on the backend service
  (which has no `TimeoutStopSec`, so a slow stop fell back to systemd's
  90-second default). Fixed: both functions now give Chrome a 2-second grace
  period, then SIGKILL — unconditional at the OS level, so it can't be slow
  for the same reasons SIGTERM can be — and the session script's backend
  stop is now `--no-block` so it can never hold up the desktop handoff
  either way. Verified locally that the escalation actually reaches SIGKILL
  against a process that ignores SIGTERM, and that a normal fast-exiting
  process is detected immediately rather than always eating the grace
  period (an actual bug caught along the way — see docs/TODO.md).
  *Unverified on the real PC* — needs an actual "Go to desktop" press to
  confirm the full round-trip is fast again.

## [2.2.0]

Two new remote-connectivity features.

### Added

- **KDE Connect pairing (Settings → Remote connect)**: pair a phone running
  the KDE Connect app as a remote control. TV Home only handles pairing —
  once paired, KDE Connect's own daemon injects mouse/keyboard events from
  the phone's "Remote input" plugin via XTest directly into the X session,
  so there's no TV-Home-specific input-routing code. Works both ways: pair
  with a reachable phone from the list, or accept/reject an incoming
  request a phone already sent. `install.sh` installs the `kdeconnect`
  package (best-effort — won't fail the rest of the install if unavailable).
- **Bluetooth PIN/passkey pairing**: some devices (older peripherals needing
  a fixed PIN, or numeric-comparison pairing) need something to answer
  BlueZ's pairing-agent callbacks — without one registered, those pairings
  just failed outright with no explanation. Registers a `KeyboardDisplay`
  pairing agent the first time you connect to anything; a PIN device now
  brings up the on-screen keyboard, a passkey-confirmation device shows a
  yes/no dialog with the code to check against the device's own display.

## [2.1.3]

Fixes "Go to desktop" dropping to a black screen instead of the real XFCE
desktop, reported after confirming the autologin flow works end-to-end.

### Fixed

- **"Go to desktop" left a black screen, no panel, no desktop icons.**
  `tv-home-session.sh` starts `xfwm4 --compositor=off` and `xbindkeys` as
  background jobs before its main loop. `to_desktop()` hands off to the
  regular desktop with `exec startxfce4` — but `exec` only replaces the
  script's own process; those backgrounded jobs are orphaned, not killed,
  and keep running. The old `xfwm4` was still holding the window-manager
  selection on the X display, so `startxfce4`'s own window manager could
  never take over, leaving just the dark `xsetroot` background from TV
  Home's startup with no panel or desktop icons on top of it. Fixed:
  `to_desktop()` now kills both before handing off. *Unverified on the real
  PC* — needs a real "Go to desktop" press to confirm.

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
