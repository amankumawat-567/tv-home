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
global Home/volume keys). The compositor setting (off, confirmed on real
hardware) is the one item in this list that's already been checked there.

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
  before writing the fix; the fix itself still needs a real reinstall to
  verify the prompt now shows up end-to-end.

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
  report and confirmed `install.sh --check` now runs to completion; still
  needs a real reinstall to confirm the autologin prompt itself appears.

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
