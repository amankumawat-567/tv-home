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
      xbindkeys, systemd unit, installer/uninstaller. *Unverified* — written
      to spec; see `session/README.md` for exactly what to check once it's on
      the real PC. (The crash-counting logic was unit-tested standalone in
      bash outside the actual session script.)
- [x] **M6 Bluetooth** — scan/pair/connect/forget, no-adapter state.
      *The "no adapter" empty state is verified* (this PC has none yet
      either); pairing/connecting over `system/bluetooth.py` is *unverified*.
- [x] **M7 Polish** — display settings + auto-revert, date/time, toasts,
      screensaver, first-run groundwork. *Mixed*: toasts/screensaver/UI
      verified; `xrandr`/`xset` calls in `system/display.py` are
      *unverified*. Phone-typing (QR → local web page) and a dedicated
      first-run wizard screen are **not built yet** (see below).
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

- [ ] First-run setup wizard (Y4: Wi-Fi, pair a remote, pick apps on first
      boot) — currently you'd configure each of these from Settings
      individually; there's no guided first-run flow.
- [ ] Phone-typing via QR code (I2) — the on-screen keyboard covers every
      text field, but there's no "scan a QR code, type on your phone" path
      yet.
- [ ] Remote key remapping / learn mode (I3, P2 — lowest priority in the PRD).
- [ ] Wallpaper slideshow is a local-only UI toggle right now
      (`settings/WallpaperPage.tsx`) — it doesn't persist to the backend or
      actually rotate wallpapers on a timer yet. (A starter pack of 8 real
      photos *is* seeded by `session/install.sh` now — see `wallpapers/`.)
- [ ] A real Material Symbols icon set (see `docs/DESIGN.md`'s "Known gaps").

## Needs the real PC to finish verifying

Everything under `backend/tv_home/system/` and `session/` — see each file's
own "NOT RUNNABLE on this macOS sandbox" header and `session/README.md`'s
verification checklist (10 cold boots, the 3-crash fallback, Ctrl+Alt+D,
global Home/volume keys, the compositor requirement).

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
