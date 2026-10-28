# TV Home session (OS integration)

The files here make the backend + frontend *be* the Xubuntu desktop session on
the real PC. **Nothing in this folder runs on macOS or any non-Linux
sandbox** — it needs X11, `xfwm4`, `xbindkeys`, `systemd --user` and LightDM.
Everything was written to the PRD's spec and to v1's already-proven patterns
(the `/proc`-based window closing), but most of it hasn't been run end-to-end
— treat it as a first draft to verify on the real machine, not as tested
code. The compositor setting (below) is the one exception: it's been
confirmed directly on the target hardware.

## Install

From a source checkout (builds the frontend — needs `node`/`npm`):

```sh
./session/install.sh
```

From a downloaded release (ships a prebuilt frontend, so `node`/`npm` aren't
needed on the target machine at all — see the top-level README's "Install"
section):

```sh
./session/install.sh --from-release /path/to/extracted/tv-home-X.Y.Z
```

This is also how Settings → About's "Update" button re-installs: it
downloads the latest release tarball and runs this same installer against it
(`backend/tv_home/system/update.py`), so there's only one install code path
to verify.

Either way, it sets up a backend virtualenv under `~/.local/share/tv-home`,
and installs:

- `/usr/local/bin/tv-home-session` — the session script
- `/usr/share/xsessions/tv-home.desktop` — so "TV Home" appears as a session
  choice on the LightDM login screen
- `~/.config/tv-home/xbindkeysrc` — global hotkeys (Home, volume, recovery)
- `~/.local/bin/tv-home-recover` — Ctrl+Alt+D's recovery command
- `~/.config/systemd/user/tv-home-backend.service` — the backend process

Any existing file at those system paths is backed up to `<path>.tv-home-orig`
before being overwritten (once).

## Autologin

On a fresh interactive install (not an update, not `--from-release`),
`install.sh` asks whether to boot straight into TV Home and as which user,
then writes `/etc/lightdm/lightdm.conf.d/50-tv-home.conf` itself (backed up
like every other system file it touches, if one already existed there):

```ini
[Seat:*]
autologin-user=YOURUSER
autologin-session=tv-home
```

It only *asks* — it never assumes — because this setting is shared across
every user on the machine, not scoped to TV Home. The prompt is skipped
(leaving autologin off) when: it's already configured, the run is
non-interactive (no TTY — this is also how the backend's own self-update
re-invokes this script, so an update never silently changes your login
screen), or the machine has no LightDM at all. Say no, or skip it, and you
can still select "TV Home" by hand from the session chooser at login — or
re-run `install.sh` later to be asked again.

## Uninstall

```sh
./session/uninstall.sh          # keeps your apps/settings
./session/uninstall.sh --purge  # also removes ~/.config/tv-home and the installed app
```

Removes the autologin config too, if install.sh wrote one.

## What to verify on the real PC (from the PRD's own build-plan checks)

- **10 cold boots** reach Home with no desktop flash and no login screen.
- **Killing the session 3 times** in under 5 minutes (`pkill -f tv-home-session`)
  falls back to the regular desktop, per `tv-home-session.sh`'s crash counter.
- **Ctrl+Alt+D** reaches the desktop even with the backend killed outright
  (`tv-home-recover.sh` doesn't depend on it).
- **Home, volume keys** work while a streaming app has focus (grabbed globally
  by `xbindkeys`, not by the frontend's own JS key handling).
- **If you ever see a black Chrome window**: this is the failure mode that
  originally came up with the compositor off, inside a full XFCE desktop.
  `tv-home-session.sh` runs `xfwm4 --compositor=off` because this dedicated
  from-boot xsession has been confirmed not to hit that bug (no desktop or
  other compositor effects running at all) — if it ever resurfaces here,
  switch that line back to `--compositor=on` as a first fix, at the cost of
  a little more CPU.
