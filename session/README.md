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

```sh
./session/install.sh
```

Run this from *either* a source checkout (needs `node`/`npm` to build the
frontend) *or* an extracted release download (ships a prebuilt
`frontend/dist`, so `node`/`npm` are never needed) — which one it's in is
auto-detected by what's actually on disk (a `frontend/dist` folder vs. a
`frontend/package.json`), not by how the script was invoked or what the
containing folder is named. Extract the release tarball anywhere, under any
name, and this just works.

`./session/install.sh --from-release /path/to/extracted/release` additionally
lets you point it at a directory *other than the one this script lives in* —
this is how Settings → About's "Update" button re-installs non-interactively
(`backend/tv_home/system/update.py` downloads the latest release, extracts
it to a temp dir, and runs this exact flag against it), so there's only one
install code path to verify for both a manual install and a self-update.

Either way, everything is copied into a fixed location,
`~/.local/share/tv-home` — nothing here ever points back at wherever you
extracted or cloned from, so deleting that folder afterwards is safe. It also
sets up a backend virtualenv there, and installs:

- `/usr/local/bin/tv-home-session` — the session script
- `/usr/share/xsessions/tv-home.desktop` — so "TV Home" appears as a session
  choice on the LightDM login screen
- `~/.config/tv-home/xbindkeysrc` — global hotkeys (Home, volume, recovery)
- `~/.local/bin/tv-home-recover` — Ctrl+Alt+D's recovery command
- `~/.config/systemd/user/tv-home-backend.service` — the backend process
- `/etc/polkit-1/rules.d/46-tv-home.rules` — see "Power actions" below

Any existing file at those system paths is backed up to `<path>.tv-home-orig`
before being overwritten (once).

## Autologin

On a fresh interactive install (not an update, not `--from-release`),
`install.sh` asks whether to boot straight into TV Home and as which user,
then writes `/etc/lightdm/lightdm.conf.d/90-tv-home.conf` itself:

```ini
[Seat:*]
autologin-user=YOURUSER
autologin-session=tv-home
```

The `90-` prefix is deliberate: a stock Ubuntu/Xubuntu install commonly
already has its own autologin snippet (typically
`lightdm.conf.d/50-autologin.conf`, pointing at the regular `xubuntu`
session), and LightDM applies `conf.d/*.conf` files in lexical order with
later files winning — `90-tv-home.conf` loads after any such default without
needing to touch it. If one is found, the installer prints it before asking
so you can see exactly what's there.

It only *asks* — it never assumes — because this setting is shared across
every user on the machine, not scoped to TV Home. The prompt reads from
`/dev/tty` directly (the same thing `sudo` already does for its own password
prompt), so it still shows up even when the script was invoked in a way that
leaves stdin non-interactive but a real terminal is attached. The prompt is
skipped (leaving autologin off) only when: it's already configured, there's
no controlling terminal at all (this is also how the backend's own
self-update re-invokes this script, so an update never silently changes your
login screen), or the machine has no LightDM at all. Say no, or skip it, and
you can still select "TV Home" by hand from the session chooser at login —
or re-run `install.sh` later to be asked again.

## Power actions (sleep/restart/shut down/go to desktop)

Settings → Power calls logind over D-Bus (`backend/tv_home/system/power.py`)
for sleep/restart/shut down. Logind's default policy requires interactive
authentication for these unless it can tell the calling session is "active"
on a local seat — not something a custom xsession run through a
`systemd --user` service reliably satisfies in every setup — so
`install.sh` installs a polkit rule
(`polkit/46-tv-home.rules.template` → `/etc/polkit-1/rules.d/46-tv-home.rules`,
with the real username substituted in) granting the installing user
passwordless use of logind's power-off/reboot/suspend actions specifically.
It's applied on every install/update, not asked about, since — unlike
autologin — it only ever affects the one account TV Home runs as.

"Go to desktop" doesn't go through logind at all: it writes the same
sentinel file as before, but now also closes TV Home's own shell window
(`chrome.close_shell()`) rather than just killing the backend process, which
never actually caused anything to happen — `tv-home-session.sh`'s foreground
wait is on the *Chrome window*, not the backend, so the old approach left it
blocked forever waiting for a window that was never going to exit.

Once that wait returns, the script's `to_desktop()` also kills its own
backgrounded `xfwm4`/`xbindkeys` before `exec`-ing `startxfce4` — `exec`
replaces the script's own process but leaves orphaned background jobs
running, and a leftover `xfwm4` still holding the window-manager selection
on the display meant `startxfce4`'s own window manager could never take
over, leaving a black screen (just the `xsetroot` background, no panel, no
desktop icons) instead of a real desktop.

## Checking status

```sh
./session/install.sh --check
```

Prints the installed path and version, whether the xsession files are in
place, every `autologin-user`/`autologin-session` line found across
`/etc/lightdm/lightdm.conf` and `lightdm.conf.d/*.conf` (in the order
LightDM would apply them), whether the polkit rule is installed and for
which user, the systemd `--user` service's status, and whether the backend
answers on `http://127.0.0.1:8000`. Doesn't install or change anything.

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
- **Sleep, restart, shut down and Go to desktop** from Settings → Power with
  no password prompt (needs `/etc/polkit-1/rules.d/46-tv-home.rules` —
  `install.sh --check` confirms it's present). If one of these reports
  "Not allowed" specifically, the polkit rule is missing or polkit didn't
  pick it up (`sudo systemctl restart polkit` and retry).
- **If you ever see a black Chrome window**: this is the failure mode that
  originally came up with the compositor off, inside a full XFCE desktop.
  `tv-home-session.sh` runs `xfwm4 --compositor=off` because this dedicated
  from-boot xsession has been confirmed not to hit that bug (no desktop or
  other compositor effects running at all) — if it ever resurfaces here,
  switch that line back to `--compositor=on` as a first fix, at the cost of
  a little more CPU.
