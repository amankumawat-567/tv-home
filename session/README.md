# TV Home session (OS integration)

The files here make the backend + frontend *be* the Xubuntu desktop session on
the real PC. **Nothing in this folder runs on macOS or any non-Linux
sandbox** — it needs X11, `xfwm4`, `xbindkeys`, `systemd --user` and LightDM.
Everything was written to the PRD's spec and to v1's already-proven patterns
(the `/proc`-based window closing, the X11 compositor requirement), but has
not been run end-to-end. Treat it as a first draft to verify on the real
machine, not as tested code.

## Install

```sh
./session/install.sh
```

Builds the frontend, sets up a backend virtualenv under
`~/.local/share/tv-home`, and installs:

- `/usr/local/bin/tv-home-session` — the session script
- `/usr/share/xsessions/tv-home.desktop` — so "TV Home" appears as a session
  choice on the LightDM login screen
- `~/.config/tv-home/xbindkeysrc` — global hotkeys (Home, volume, recovery)
- `~/.local/bin/tv-home-recover` — Ctrl+Alt+D's recovery command
- `~/.config/systemd/user/tv-home-backend.service` — the backend process

Any existing file at those system paths is backed up to `<path>.tv-home-orig`
before being overwritten (once).

## Enabling autologin (manual, on purpose)

Autologin config is shared across every user on the machine, so the installer
doesn't touch it automatically. To boot straight into TV Home as `YOURUSER`,
create `/etc/lightdm/lightdm.conf.d/50-tv-home.conf`:

```ini
[Seat:*]
autologin-user=YOURUSER
autologin-session=tv-home
```

Then reboot. Until you do this, you can still select "TV Home" by hand from
the session chooser on the login screen.

## Uninstall

```sh
./session/uninstall.sh          # keeps your apps/settings
./session/uninstall.sh --purge  # also removes ~/.config/tv-home and the installed app
```

Also remove `/etc/lightdm/lightdm.conf.d/50-tv-home.conf` if you enabled
autologin, then reboot.

## What to verify on the real PC (from the PRD's own build-plan checks)

- **10 cold boots** reach Home with no desktop flash and no login screen.
- **Killing the session 3 times** in under 5 minutes (`pkill -f tv-home-session`)
  falls back to the regular desktop, per `tv-home-session.sh`'s crash counter.
- **Ctrl+Alt+D** reaches the desktop even with the backend killed outright
  (`tv-home-recover.sh` doesn't depend on it).
- **Home, volume keys** work while a streaming app has focus (grabbed globally
  by `xbindkeys`, not by the frontend's own JS key handling).
- **Compositor on**: if you ever see a black Chrome window, check `xfwm4` is
  running with `--compositor=on` — it was required on this hardware's Intel
  GPU even though it costs a little more CPU.
