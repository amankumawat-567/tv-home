# TODO

Status against the PRD's own 8-milestone build plan (`docs/PRD.pdf`, "Build
plan"). "Verified" means tested in this repo (pytest, Playwright, or a build);
"unverified" means written to spec but never run, because it depends on
hardware/OS this project wasn't developed on (real D-Bus, X11, systemd).

## Done

- [x] **M0 Foundation** — repo layout, design tokens, focus engine, backend
      skeleton with mock mode. *Verified.*
- [x] **M1 Home** — top bar, Favourites row, wallpaper + greeting. *Verified*
      (Playwright screenshots + arrow-key reachability at 1366×768 and
      1920×1080, `frontend/tests/e2e/`).
- [x] **M2 Apps** — kiosk launch/close, launch screen, App Store with
      add-a-website. *Verified* (install/remove/launch logic under pytest;
      the launch round-trip itself needs a real `google-chrome` binary on
      PATH, which this dev machine doesn't have — see
      `backend/tv_home/chrome.py`).
- [x] **M3 Quick settings + Sound + Power** — panel UI, volume, power confirm
      dialogs. *UI verified*; `wpctl`/logind calls themselves are
      *unverified* (no PipeWire/D-Bus here).
- [x] **M4 Wi-Fi + on-screen keyboard** — network list, connect/forget flow,
      the QWERTY keyboard. *UI and mock flow verified*; real
      NetworkManager calls in `system/wifi.py` are *unverified*.
- [x] **M5 Session and recovery** — session script, LightDM xsession,
      xbindkeys, systemd unit, installer/uninstaller, a `--check` status
      command. *Partially field-verified* — see "Fixed from real-hardware
      testing" below for what's actually been run on the target PC; the rest
      is still written-to-spec. (The crash-counting logic was separately
      unit-tested standalone in bash.)
- [x] **M6 Bluetooth** — scan/pair/connect/forget, no-adapter state.
      *The "no adapter" empty state is verified* (this PC has none yet
      either); pairing/connecting over `system/bluetooth.py` is *unverified*.
- [x] **M7 Polish** — display settings + auto-revert, date/time, toasts,
      screensaver, first-run groundwork. *Mixed*: toasts/screensaver/UI
      verified; `xrandr`/`xset` calls in `system/display.py` are
      *unverified*. The screen-off timer is now app-aware — launching an app
      inhibits it and Home re-arms it (`display_provider.inhibit()`/
      `restore()`), so a movie with no remote input for N minutes doesn't get
      blanked mid-playback; the setting itself now persists across a backend
      restart via `settings.json`, applied again on boot. Phone-typing (QR →
      local web page) and a dedicated first-run wizard screen are now built —
      see "Added in 2.1.0" below.
- [x] **Y6 Update from GitHub releases** — Settings → About checks
      `GITHUB_REPO`'s latest release and installs it with one select.
      *Check is verified live* against the real repo
      (`backend/tv_home/system/update.py` correctly found v2.0.0 and its
      asset URL); *apply is unverified* (it re-runs `session/install.sh`, so
      it inherits that script's own unverified status). CI
      (`.github/workflows/ci.yml`) and the release packaging
      (`.github/workflows/release.yml`) are both live at
      [github.com/amankumawat-567/tv-home](https://github.com/amankumawat-567/tv-home)
      and have run successfully.

## Not built yet

Nothing left from the PRD's own backlog — the remaining five items (first-run
wizard, phone-typing, remote remapping, wallpaper slideshow persistence, real
Material Symbols icons) are done; see "Added in 2.1.0" below.

## Needs the real PC to finish verifying

Everything under `backend/tv_home/system/` and `session/` — see each file's
own "NOT RUNNABLE on this macOS sandbox" header and `session/README.md`'s
verification checklist (10 cold boots, the 3-crash fallback, Ctrl+Alt+D,
global Home/volume keys). Confirmed on real hardware so far: the compositor
setting (off), and now `install.sh`'s autologin flow end-to-end (see "Fixed
from real-hardware testing (2.1.2)" below) — reboot-to-TV-Home itself still
needs confirming.

## Fixed from real-hardware testing (2.0.2)

A bug report from actually installing on the target Xubuntu 26.04 PC:

- **Release installs required node/npm and crashed.** `install.sh` only
  skipped the frontend build when invoked as `--from-release <dir>`; running
  it plainly (as anyone extracting the tarball would) always assumed a
  source checkout. Fixed: whether to build is now auto-detected from what's
  on disk (`frontend/dist` present vs. `frontend/package.json` present),
  regardless of how the script was invoked or what the containing folder is
  named. Verified locally against a fake release-shaped directory with a
  deliberately non-"tv-home" folder name.
- **"Installs into the download folder" — audited, not reproduced.** Every
  path that matters at runtime (the systemd unit's `ExecStart`/
  `WorkingDirectory`, `main.py`'s static-frontend resolution, the pip
  editable install) already resolves against the fixed
  `~/.local/share/tv-home`, never the source/download directory — this was
  very likely a symptom of the bug above (the script crashed before the copy
  step ever ran, so nothing was installed at all). No code change beyond the
  fix above; call it out again if it still reproduces once that's in place.
- **A pre-existing autologin config silently won.** A stock Xubuntu install
  commonly already has `lightdm.conf.d/50-autologin.conf` pointing at the
  regular `xubuntu` session. Fixed: TV Home's own config moved to
  `90-tv-home.conf` (loads after any such default, so it wins without
  touching the other file), and the installer now scans for and prints any
  conflicting autologin config before asking. Verified standalone against a
  simulated `50-autologin.conf`.
- **Added `./session/install.sh --check`** — installed path/version, session
  file presence, every autologin line found (in LightDM's own load order),
  the systemd service's status, and whether the backend answers on
  `127.0.0.1:8000`, without installing or changing anything.

## Fixed from real-hardware testing (2.0.3)

A follow-up setup/boot spec and a specific bug report: "power features are
not working like shutdown, go to desktop, restart and sleep."

- **"Go to desktop" could never have worked.** It killed the *backend*
  process and left a sentinel file, expecting `tv-home-session.sh`'s loop to
  notice and hand off to the desktop — but that loop is blocked in a
  foreground wait on the *Chrome shell window*, not the backend, so killing
  the backend alone never caused it to proceed. Fixed: `chrome.close_shell()`
  closes TV Home's own window specifically (go_home() deliberately excludes
  it, since the Home key must *not* close the shell) — found by re-reading
  the two functions side by side, confirmed via a unit test that they're
  distinct, and the PID-selection logic exercises the same `/proc` code path
  `go_home()` already uses (Linux-only; degrades to a no-op on this sandbox).
- **Sleep/restart/shut down likely failed on authorization, not code.** These
  call logind over D-Bus with `interactive=False`; without a polkit rule
  explicitly granting the TV Home user passwordless access, logind's default
  policy requires authentication that nothing in a kiosk session can
  provide, and the call fails immediately. Added
  `session/polkit/46-tv-home.rules.template`, installed (username
  substituted in) by `install.sh` on every install/update. `power.py` also
  now surfaces "Not allowed — check the polkit rule…" specifically for an
  auth failure instead of a generic error, so this is diagnosable from the
  UI alone. *Unverified beyond JS-syntax-checking the rule* — needs the real
  PC; `install.sh --check` reports whether the rule file is present.
- **Not yet addressed from the same spec**: point 20's broader ask (Wi-Fi/
  Bluetooth/display *also* needing no-password polkit coverage) — only
  logind's power actions got a rule here, scoped to the specific "power
  features" bug report. NetworkManager/BlueZ policy is typically more
  permissive by default for a local active user, but hasn't been confirmed
  on this hardware either.

## Added in 2.1.0

The five items that were left in "Not built yet" above:

- **First-run setup wizard (Y4)** — `frontend/src/screens/FirstRunWizard.tsx`.
  A step machine (Welcome → Wi-Fi → Remote → Apps → Home) shown once, gated on
  a `firstRunComplete` flag in `settings.json`. Back steps backward, Home
  skips straight to the real Home screen and marks it done either way.
  *Verified* end-to-end (`frontend/tests/e2e/first-run.spec.ts`), both the
  step flow and that it never returns after completion.
- **Phone-typing via QR code (I2)** — `backend/tv_home/phone_type.py` and
  `routes/phone_type.py` hand out a short-lived token and serve a tiny
  standalone page at `/type/<token>` (no `/api` prefix — this is the URL
  actually opened from the phone); the on-screen keyboard
  (`OnScreenKeyboard.tsx`) shows a QR code for it and polls the session,
  submitting the moment the phone taps Done. Token is a 128-bit
  `secrets.token_urlsafe(16)` — judged adequate auth for a personal LAN
  device with no login anywhere else in the product. *Verified*
  (`frontend/tests/e2e/phone-type.spec.ts` drives the phone side via direct
  HTTP calls, the same way a real phone's page would).
- **Remote key remapping / learn mode (I3)** — `backend/tv_home/keymap.py` +
  `routes/remote.py`, Settings → Remote
  (`frontend/src/settings/RemotePage.tsx`). Each of the 8 actions
  (up/down/left/right/select/back/home/menu) can be rebound by pressing a key
  while in "learn mode"; `frontend/src/state/keymap.ts` is consulted by every
  check in `useKeyNav.ts` (user override first, hardcoded default otherwise).
  *Verified* (`backend/tests/test_routes.py::test_keymap_remap_persists_and_resets`).
- **Wallpaper slideshow persistence** — `wallpaper.py` gained
  `slideshow_settings()`/`set_slideshow()`, persisted to `settings.json`; a
  new background task (`slideshow.py`, started from `main.py`'s lifespan)
  checks every 60s and advances the wallpaper on the configured interval.
  `settings/WallpaperPage.tsx` now reads/writes this instead of holding
  local-only state. *Verified*
  (`backend/tests/test_routes.py::test_wallpaper_slideshow_persists`).
- **A real Material Symbols icon set** — `frontend/src/components/Icons.tsx`
  now uses actual Apache-2.0 path data (fetched from the
  `@material-symbols/svg-400` npm package, a mirror of Google's
  material-design-icons repo) instead of hand-rolled stand-ins, bundled
  inline so there's no runtime network dependency. `WifiIcon` stays
  hand-drawn on purpose — it renders 0-4 bars from live signal strength,
  which no single static glyph can do. Closes the gap noted in
  `docs/DESIGN.md`'s "Known gaps". *Verified visually* (Playwright
  screenshots of the top bar, Quick Settings panel, and the Wi-Fi settings
  page's lock icons at 1920×1080 — no regressions).

## Fixed from real-hardware testing (2.1.1)

A real install on Xubuntu 26.04 completed with no errors (`install.sh --check`
showed the install, session file, and systemd unit all present) but never
booted into TV Home after reboot.

- **Autologin silently never got configured.** `configure_autologin`'s guard
  for skipping the prompt on a non-interactive run checked `[ ! -t 0 ]` (is
  stdin a terminal) — but stdin isn't always a tty even when a real terminal
  is genuinely attached, depending on exactly how the script gets invoked.
  On the reporting machine, `sudo`'s own password prompts worked fine (sudo
  reads from `/dev/tty` directly, not stdin), so the install appeared to
  complete normally, but the `read -p` autologin prompt — which does read
  from stdin — never appeared, and `/etc/lightdm/lightdm.conf.d/90-tv-home.conf`
  was simply never written. Fixed: the prompt now reads from `/dev/tty`
  directly too, matching `sudo`'s own behavior, and only gives up when
  there's truly no controlling terminal anywhere (the actual case this guard
  exists for — the backend's own non-interactive self-update, Y6). Confirmed
  the missing config file on the reporting machine via `install.sh --check`
  before writing the fix. Turned out to be a real bug but not the actual
  cause of the reported symptom — see "Fixed from real-hardware testing
  (2.1.2)" below for the fix that actually resolved it.

## Fixed from real-hardware testing (2.1.2)

The 2.1.1 fix above didn't actually fix anything on the reporting machine:
the autologin prompt still never appeared, and a follow-up `install.sh
--check` died silently right after printing the "Autologin" header, no
error message at all.

- **`set -e`/`pipefail` + "grep found nothing" was the real culprit, in two
  places.** `install.sh` greps each LightDM config file for an existing
  `autologin-user`/`autologin-session` line; on a stock system most files —
  starting with `/etc/lightdm/lightdm.conf` itself, always checked first —
  have no such line, which is the expected, normal case. But
  `var="$(grep ... | tail -1 | cut ...)"` under `set -euo pipefail` aborts
  the whole script the instant grep finds nothing, silently. This hit
  `run_doctor()`'s own scan loop (killing `--check` on its very first
  iteration, against the stock `lightdm.conf` every machine has) and,
  separately, `configure_autologin()`'s `others="$(other_autologin_configs)"`
  call (killing a real install right after the polkit rule step, before the
  autologin prompt was ever reached) — this was the actual explanation for
  "the prompt never showed up," not the `/dev/tty` issue 2.1.1 fixed, which
  was a real bug but never actually got a chance to run. Fixed by treating
  "no match" as success (`|| true`) at every one of these spots. Reproduced
  locally against the exact stock `lightdm.conf` content from the real
  report and confirmed `install.sh --check` now runs to completion.
  **Confirmed fixed on the real PC**: the autologin prompt appeared, was
  answered, and `/etc/lightdm/lightdm.conf.d/90-tv-home.conf` was written —
  this is the first fully end-to-end real-hardware confirmation of the
  autologin flow since it was first built.

## Fixed from real-hardware testing (2.1.3)

Reported right after confirming the autologin flow works: "Go to desktop"
drops to a black screen instead of the real XFCE desktop.

- **`to_desktop()` left its own `xfwm4`/`xbindkeys` running.**
  `tv-home-session.sh` starts both as background jobs before its main loop;
  `to_desktop()` hands off with `exec startxfce4`, but `exec` only replaces
  the script's own process — those backgrounded jobs are orphaned, not
  killed, and keep running. The old `xfwm4` was still holding the
  window-manager selection on the display, so `startxfce4`'s own window
  manager could never take over, leaving just the dark `xsetroot` background
  from TV Home's startup with no panel or desktop icons. Fixed:
  `to_desktop()` now kills both (captured via `$!` when they're started)
  before `exec`-ing `startxfce4`. *Unverified on the real PC* — needs an
  actual "Go to desktop" press to confirm.

## Added in 2.2.0

- **KDE Connect pairing (Settings → Remote connect)** —
  `backend/tv_home/system/kdeconnect.py`, mirrored by `mock/kdeconnect.py`.
  dbus-fast against the session bus's `org.kde.kdeconnect` service
  (`/modules/kdeconnect` daemon object, `/modules/kdeconnect/devices/<id>`
  per device) — the exact method/property names
  (`devices()`/`deviceNames()`/`requestPairing()`/`acceptPairing()`/
  `cancelPairing()`/`unpair()`, `isPaired`/`isReachable`/
  `isPairRequestedByPeer`) were taken directly from kdeconnect-kde's own
  source (`core/daemon.h`, `core/device.h`,
  `dbusinterfaces/dbusinterfaces.cpp`), not guessed from CLI output or docs.
  TV Home only handles pairing; once paired, KDE Connect's own daemon
  injects input from the phone's "Remote input" plugin via XTest directly,
  with no TV-Home-specific input code at all. `install.sh` installs the
  `kdeconnect` package in its own best-effort `apt-get` call so a missing
  package can't fail the rest of the install. *Verified*: the full UI flow
  against the mock provider (box-initiated pairing and accepting/rejecting
  an incoming request), `backend/tests/test_routes.py`'s kdeconnect tests,
  and `frontend/tests/e2e/remote-connectivity.spec.ts`. *Unverified*: the
  real D-Bus calls themselves — needs KDE Connect actually installed and a
  real phone on the real PC (no session D-Bus bus or kdeconnectd on this
  macOS sandbox).
- **Bluetooth PIN/passkey pairing** — `system/bluetooth.py` gained a
  `org.bluez.Agent1` implementation (`_PairingAgent`, capability
  `KeyboardDisplay`) registered the first time `connect()` is called;
  `RequestPinCode`/`RequestPasskey`/`RequestConfirmation`/
  `RequestAuthorization` bridge to the UI via a one-pending-request-at-a-time
  slot (`pairing_request()`/`respond_pairing_request()`,
  `GET`/`POST /api/bluetooth/pairing`), the same side-channel-poll shape
  `phone_type.py` already uses. `AuthorizeService` auto-approves (the device
  is already trusted by then) rather than prompting per-service. Mirrored in
  `mock/bluetooth.py` with two dedicated mock devices (a PIN-only one, a
  passkey-confirmation one) so the full handshake — including a *wrong* PIN
  correctly failing — is exercised without real hardware. The on-screen
  keyboard handles PIN/passkey entry; a yes/no dialog (reusing
  `ConfirmDialog`, which gained an `onCancel` hook for this) handles
  passkey confirmation. *Verified* against the mock agent (correct and
  incorrect PIN, accept and reject confirmation) via
  `backend/tests/test_routes.py` and
  `frontend/tests/e2e/remote-connectivity.spec.ts`. *Unverified*: the real
  BlueZ agent registration and callbacks — needs a real Bluetooth adapter
  and a PIN/passkey device on the real PC.

## Fixed from real-hardware testing (2.2.1)

Reported after confirming the "Go to desktop" black-screen fix: the whole
thing now takes almost 2 minutes where v1 (Flex Launcher) was instant.

- **SIGTERM alone, with nothing forcing Chrome to actually die promptly.**
  `chrome.go_home()`/`close_shell()` sent SIGTERM and trusted Chrome to exit
  quickly — on this hardware, a kiosk profile's cache/cookie/service-worker
  flush to a slow old disk (or one hung renderer) can leave the browser
  process alive well after SIGTERM. That delays two separate things: the
  session script's foreground wait on that exact process (closing the shell
  window is literally what lets "Go to desktop" proceed), and
  `systemctl --user stop tv-home-backend.service` in `to_desktop()`, which
  has no `TimeoutStopSec` and so falls back to systemd's default (commonly
  90s) if the backend itself is slow to stop for the same underlying reason.
  Fixed: both chrome functions now give Chrome a 2-second grace period after
  SIGTERM, then SIGKILL (unconditional at the OS level — can't be slow for
  the same reasons SIGTERM can be); the session script's stop is now
  `--no-block` so it can never hold up the handoff regardless. Found and
  fixed a real bug while building this: the liveness check
  (`os.kill(pid, 0)`) can't tell "still running" from "zombie, not yet
  reaped" for a process the backend itself spawned (a launched app's
  Chrome) — without reaping it first via `os.waitpid(pid, os.WNOHANG)`,
  *every* close would eat the full 2-second grace period even when Chrome
  exits instantly, which would have made the Home key always feel slightly
  laggy. Verified locally (not on real hardware) with a process that
  ignores SIGTERM (confirms escalation to SIGKILL within the grace period)
  and one that exits normally (confirms it's detected in ~0.1s, not 2s).
  *Unverified on the real PC* — needs an actual "Go to desktop" press to
  confirm the full round-trip is fast again; the underlying "why does
  Chrome take so long to die here" question (slow disk? one specific app?)
  is still open even if this bounds its impact either way.

## Fixed from real-hardware testing (2.2.2)

Reported right after trying KDE Connect for the first time: pairing never
worked at all ("couldn't able to connect"), and separately, all wallpapers
were reported invisible/non-switchable in Settings.

- **`kdeconnectd` never actually started.** Confirmed the same class of gap
  as the earlier autologin/black-screen bugs: this minimal kiosk X session
  runs no desktop session manager, so the `kdeconnect` package's XDG
  autostart entry (which needs one) never fires, and its D-Bus
  service-activation file alone didn't reliably pick up the slack either.
  Fixed: `tv-home-session.sh` now starts `kdeconnectd` itself, same pattern
  as `xbindkeys`, and kills it in `to_desktop()` for the same
  orphaned-process reason xfwm4/xbindkeys needed that fix in 2.1.3.
  `install.sh --check` now reports whether `kdeconnectd` is actually
  running (only meaningful inside the TV Home X session, not from a plain
  SSH shell — documented clearly since that distinction isn't obvious).
  *Unverified on the real PC* — needs an actual pairing attempt to confirm.
- **Wallpaper gallery was just a blind "Next" button; see "Added in 2.2.2"
  below for the fix** — bundled with a real latent bug caught while
  building it: `config.WALL_DIRS` was a module-level list frozen at import
  time from `USER_WALLS`, the exact "bound at import, breaks monkeypatch
  isolation" gotcha already fixed for other config values — converted to a
  `wall_dirs()` function (`backend/tv_home/config.py`).

## Added in 2.2.2

- **A real TV-remote layout for KDE Connect** — pairing now also writes the
  phone's KDE Connect "Run Command" plugin config with a D-pad (Up/Down/
  Left/Right/OK/Back/Home/Menu/volume), each button running `xdotool key
  <X>` with the same X11 keysym names a real keyboard sends, matched
  against `frontend/src/state/keymap.ts`'s defaults (`backend/tv_home/
  system/kdeconnect.py`'s `TV_REMOTE_COMMANDS`/`install_tv_remote()`). The
  config file format and escaping (a Qt `QSettings` INI file) came directly
  from kdeconnect-kde's own source (`core/kdeconnectpluginconfig.cpp`,
  `models/commandsmodel.cpp`) and were verified by round-tripping a
  generated file through a real `QSettings` instance (PySide6, installed
  temporarily for this one check) — not guessed. `install.sh` now also
  installs `xdotool`. *Unverified beyond the round-trip check*: needs a
  real pairing on the real PC to confirm the phone's app actually shows the
  buttons without reopening it.
- **A real wallpaper gallery (Settings → Wallpaper)** — was previously just
  a single preview + a blind "Next wallpaper" button with no way to see or
  jump to a specific one. Added `GET /api/wallpaper/list`,
  `GET /wallpaper/{index}` (thumbnails), `POST /api/wallpaper/set`
  (`backend/tv_home/wallpaper.py`'s `wallpaper_list()`/`set_wallpaper()`),
  and a thumbnail-grid frontend (`settings/WallpaperPage.tsx`) with the
  current wallpaper marked. Also fixed the underlying staleness bug:
  `/wallpaper` serves different content from the same URL once the
  selection changes, which browsers can cache past the point it's stale —
  added `Cache-Control: no-store` on that endpoint and a `wallpaperVersion`
  cache-busting token in `AppState` so the Home screen's background
  reliably updates too. *Verified*: `backend/tests/test_routes.py`'s new
  wallpaper tests, and a manual Playwright pass with screenshots showing
  all 8 starter-pack wallpapers in the gallery, selection moving the
  "current" marker, and the Home screen's background actually changing.
  E2E coverage intentionally skipped — unlike apps, wallpapers come purely
  from the filesystem with no API to seed them, so a CI run (no wallpapers
  present) would only ever exercise the empty state, not the gallery.

## Added in 2.2.3

- **"Set up TV remote" for already-paired KDE Connect devices** (Settings →
  Remote connect) — follow-up to 2.2.2's TV remote feature, after a real
  pairing (a Mac running the actual KDE Connect desktop app, on a confirmed
  v2.2.2 install) showed no Run Commands at all. Root cause:
  `pair()`/`accept()` only write the config at the exact moment pairing
  happens, so anything paired before the feature existed, or through any
  path other than TV Home's own Settings page, never got it — and there was
  no way to fix that without unpairing and re-pairing. Added a
  `POST /api/kdeconnect/install-remote` route and
  `system/kdeconnect.py`'s `install_remote()`, surfaced as a "Set up TV
  remote" row on every paired device, safe to run any number of times.
  *Verified*: `backend/tests/test_routes.py`'s new test and a manual
  Playwright pass (screenshots showing the row and the success toast).
  *Unverified on the real PC*: needs the actual already-paired device (the
  Mac from the real-hardware report) to confirm Run Commands actually
  populates after using this.

## Open product decisions (from the PRD, not yet re-decided)

The PRD left these open; defaults were applied so implementation wasn't
blocked on them (see `docs/PRD.pdf`'s "Open questions" and the plan this was
built from) — revisit if you want a different answer:

- Project name: kept as "TV Home".
- License: MIT (`LICENSE`).
- Scope: this PC's X11/xfwm4 session only, no Wayland, no other screen sizes.
- Reference remote: none assumed — the key map is implemented as plain
  keyboard/`XF86` consumer-control events, which is how IR/Bluetooth remotes
  already surface on Linux via evdev/X11.
