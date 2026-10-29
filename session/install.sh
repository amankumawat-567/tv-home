#!/usr/bin/env bash
# Installs (or updates) TV Home 2.0 onto a Xubuntu PC: puts the frontend and
# backend into a fixed location (~/.local/share/tv-home — never the folder
# this script was run from, so deleting your Downloads afterwards is safe),
# installs the X11 session, global hotkeys, the systemd user unit, and the
# recovery command. Backs up any system file it touches before changing it
# (Y5).
#
# From a source checkout (builds the frontend here — needs node/npm):
#   ./session/install.sh
#
# From a downloaded release (ships a prebuilt frontend/dist — node/npm are
# never needed, from any folder name: whether a prebuilt frontend exists is
# auto-detected, not inferred from how this script was invoked):
#   ./session/install.sh
#
# From an arbitrary extracted release directory, not the one this script
# lives in (this is also how the backend's own self-update, Y6, re-installs
# non-interactively):
#   ./session/install.sh --from-release /path/to/extracted/release
#
# Status check — installed path, session file, autologin, watchdog, backend
# health — without installing or changing anything:
#   ./session/install.sh --check
#
# NOT RUNNABLE on this macOS dev sandbox (needs apt, systemd, LightDM, X11) —
# written to spec; run and verify on the real PC. On a fresh interactive
# install it offers to enable autologin into this session (skipped entirely
# on an update, non-interactive run, or a machine with no LightDM) — see
# configure_autologin() below and session/README.md.
set -euo pipefail

# Loads last among lightdm.conf.d/*.conf (lexically after any "NN-..." file
# using a two-digit prefix below 90, which covers every default Ubuntu/
# Xubuntu autologin snippet seen in the wild) so TV Home's autologin wins
# over a pre-existing one without having to touch that other file at all.
LIGHTDM_CONF=/etc/lightdm/lightdm.conf.d/90-tv-home.conf
POLKIT_RULE=/etc/polkit-1/rules.d/46-tv-home.rules

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/.local/share/tv-home"
CONFIG_DIR="$HOME/.config/tv-home"
FROM_RELEASE=false

if [ "${1:-}" = "--check" ]; then
  REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
elif [ "${1:-}" = "--from-release" ]; then
  FROM_RELEASE=true
  REPO_ROOT="$(cd "$2" && pwd)"
  SCRIPT_DIR="$REPO_ROOT/session" # use the release's own session/ files, not this script's
else
  REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
fi

log() { echo "==> $*"; }

backup() {
  # Back up a file this installer is about to overwrite — once, so repeated
  # installs don't clobber the original with an already-TV-Home-ified copy.
  local path="$1"
  if [ -e "$path" ] && [ ! -e "$path.tv-home-orig" ]; then
    sudo cp -a "$path" "$path.tv-home-orig" 2>/dev/null || cp -a "$path" "$path.tv-home-orig"
    log "Backed up $path -> $path.tv-home-orig"
  fi
}

other_autologin_configs() {
  # Every file that sets autologin-user/-session besides our own, in the
  # order LightDM would actually load them (lightdm.conf first, then
  # conf.d/*.conf alphabetically) — so a default Ubuntu/Xubuntu install's own
  # autologin snippet (commonly .../lightdm.conf.d/50-autologin.conf,
  # targeting the stock "xubuntu" session) is found and called out by name.
  local f
  for f in /etc/lightdm/lightdm.conf /etc/lightdm/lightdm.conf.d/*.conf; do
    [ -e "$f" ] || continue
    [ "$f" = "$LIGHTDM_CONF" ] && continue
    grep -qE '^\s*autologin-(user|session)\s*=' "$f" 2>/dev/null && echo "$f"
  done
}

configure_autologin() {
  # Autologin is system-wide (every user on the machine, via LightDM), so
  # unlike everything else this installer does, it asks first — skipped
  # entirely rather than assumed on an update, a non-interactive run (e.g.
  # the backend's own self-update, which runs this script with no TTY
  # attached), a machine with no LightDM, or one that's already configured.
  if [ ! -d /etc/lightdm ]; then
    log "LightDM not found — pick \"TV Home\" manually at the login screen"
    return
  fi
  if [ -e "$LIGHTDM_CONF" ]; then
    log "Autologin already configured ($LIGHTDM_CONF) — leaving it alone"
    return
  fi

  # read -p reads from stdin (fd 0), which isn't always the controlling
  # terminal even when one is genuinely attached — e.g. this script run as a
  # remote command string, through a task runner, or anything else that
  # leaves fd 0 non-interactive. sudo already handles exactly this by
  # prompting on /dev/tty directly instead of stdin; do the same here rather
  # than silently skipping whenever fd 0 merely isn't a tty. Only give up
  # when there's truly no controlling terminal at all (e.g. the backend's own
  # self-update, run detached with no TTY anywhere) — that's the real
  # non-interactive case this guard exists for.
  local tty=/dev/tty
  if [ ! -r "$tty" ] || [ ! -w "$tty" ]; then
    if [ ! -t 0 ]; then
      log "No controlling terminal available — skipping the autologin prompt (see session/README.md to enable it later)"
      return
    fi
    tty=/dev/stdin
  fi

  local others
  others="$(other_autologin_configs)"
  if [ -n "$others" ]; then
    log "Found existing autologin settings that would otherwise conflict:"
    while IFS= read -r f; do log "  - $f ($(grep -E '^\s*autologin-(user|session)\s*=' "$f" | tr '\n' ' '))"; done <<< "$others"
    log "TV Home's config ($LIGHTDM_CONF) loads after these, so it will win — nothing above is modified."
  fi

  read -r -p "==> Enable autologin straight into TV Home on boot? [y/N] " reply < "$tty"
  case "$reply" in
    [Yy]*) ;;
    *) log "Skipped autologin — pick \"TV Home\" manually at the login screen, or re-run this script later"; return ;;
  esac
  read -r -p "==> Autologin as which user? [$USER] " autologin_user < "$tty"
  autologin_user="${autologin_user:-$USER}"
  id "$autologin_user" >/dev/null 2>&1 || { echo "No such user: $autologin_user — skipping autologin." >&2; return; }

  sudo mkdir -p "$(dirname "$LIGHTDM_CONF")"
  printf '[Seat:*]\nautologin-user=%s\nautologin-session=tv-home\n' "$autologin_user" | sudo tee "$LIGHTDM_CONF" >/dev/null
  log "Autologin enabled for $autologin_user — reboot to try it (remove $LIGHTDM_CONF to undo, or run session/uninstall.sh)"
}

install_polkit_rule() {
  # Sleep/restart/shut down from the UI need this — without it, logind
  # requires interactive authentication for these actions (see
  # backend/tv_home/system/power.py's docstring), which nothing in a kiosk
  # session can answer, so the request just fails. Unlike autologin, this
  # only grants permissions to the current user's own account, so it's
  # applied unconditionally rather than asked about.
  if [ ! -d /etc/polkit-1 ]; then
    log "polkit not found — sleep/restart/shut down may prompt for a password or fail"
    return
  fi
  backup "$POLKIT_RULE"
  sudo mkdir -p "$(dirname "$POLKIT_RULE")"
  sed "s/__TV_HOME_USER__/$USER/" "$SCRIPT_DIR/polkit/46-tv-home.rules.template" | sudo tee "$POLKIT_RULE" >/dev/null
  # polkitd picks up rules.d changes via inotify on modern systems; restarting
  # it is a harmless belt-and-suspenders in case that doesn't fire.
  sudo systemctl try-restart polkit 2>/dev/null || true
  log "Installed the polkit rule for $USER ($POLKIT_RULE)"
}

run_doctor() {
  echo "TV Home — status"
  echo
  echo "Install path: $INSTALL_DIR"
  if [ -d "$INSTALL_DIR" ]; then
    echo "  present, version $(cat "$INSTALL_DIR/VERSION" 2>/dev/null || echo "unknown")"
  else
    echo "  not installed"
  fi
  echo
  echo "Session file: /usr/share/xsessions/tv-home.desktop"
  if [ -e /usr/share/xsessions/tv-home.desktop ]; then
    grep '^Exec=' /usr/share/xsessions/tv-home.desktop 2>/dev/null | sed 's/^/  /'
    if [ -x /usr/local/bin/tv-home-session ]; then
      echo "  /usr/local/bin/tv-home-session: present and executable"
    else
      echo "  /usr/local/bin/tv-home-session: MISSING or not executable"
    fi
  else
    echo "  not installed"
  fi
  echo
  echo "Autologin (checked in LightDM's own load order — last match per key wins):"
  local f u s found=false
  for f in /etc/lightdm/lightdm.conf /etc/lightdm/lightdm.conf.d/*.conf; do
    [ -e "$f" ] || continue
    u="$(grep -E '^\s*autologin-user\s*=' "$f" 2>/dev/null | tail -1 | cut -d= -f2-)"
    s="$(grep -E '^\s*autologin-session\s*=' "$f" 2>/dev/null | tail -1 | cut -d= -f2-)"
    if [ -n "$u$s" ]; then
      found=true
      echo "  $f: user=${u:-<unset>} session=${s:-<unset>}"
    fi
  done
  $found || echo "  none configured — pick \"TV Home\" manually at the login screen"
  echo
  echo "Polkit rule (sleep/restart/shut down with no password): $POLKIT_RULE"
  if [ -e "$POLKIT_RULE" ]; then
    local rule_user
    rule_user="$(grep -o 'subject.user !== "[^"]*"' "$POLKIT_RULE" 2>/dev/null | grep -o '"[^"]*"' | tr -d '"')"
    echo "  present, applies to user: ${rule_user:-unknown}"
  else
    echo "  NOT installed — these actions will likely fail or prompt for a password"
  fi
  echo
  echo "Backend service (systemd --user):"
  systemctl --user status tv-home-backend.service --no-pager -l 2>&1 | head -6 | sed 's/^/  /' || echo "  not found"
  echo
  echo "Backend health (http://127.0.0.1:8000/api/state):"
  if curl -fs -m 3 http://127.0.0.1:8000/api/state 2>/dev/null | grep -q '"user"'; then
    echo "  reachable"
  else
    echo "  NOT reachable"
  fi
}

if [ "${1:-}" = "--check" ]; then
  run_doctor
  exit 0
fi

log "Checking prerequisites"
if command -v apt-get >/dev/null; then
  sudo apt-get update -qq
  sudo apt-get install -y -qq python3-venv python3-pip xbindkeys curl rsync >/dev/null
else
  log "apt-get not found — make sure python3-venv, xbindkeys, curl and rsync are installed"
fi
command -v python3 >/dev/null || { echo "Missing required command: python3" >&2; exit 1; }

# Whether to build the frontend is auto-detected from what's actually on
# disk, never from how this script was invoked — a release tarball run
# directly (no --from-release) has a prebuilt frontend/dist and no
# frontend/package.json, so it must never require node/npm.
if [ -d "$REPO_ROOT/frontend/dist" ]; then
  log "Using the prebuilt frontend ($REPO_ROOT/frontend/dist) — no build needed"
elif [ -f "$REPO_ROOT/frontend/package.json" ]; then
  for bin in node npm; do
    command -v "$bin" >/dev/null || { echo "Missing required command: $bin (only needed when building from source)" >&2; exit 1; }
  done
  log "Building the frontend"
  (cd "$REPO_ROOT/frontend" && npm install && npm run build)
else
  echo "Neither frontend/dist nor frontend/package.json found under $REPO_ROOT — is this a real TV Home checkout or release?" >&2
  exit 1
fi

log "Installing to $INSTALL_DIR"
mkdir -p "$INSTALL_DIR" "$CONFIG_DIR"
rsync -a --delete "$REPO_ROOT/backend/tv_home" "$REPO_ROOT/backend/pyproject.toml" "$INSTALL_DIR/backend/" 2>/dev/null \
  || { mkdir -p "$INSTALL_DIR/backend"; cp -r "$REPO_ROOT/backend/tv_home" "$REPO_ROOT/backend/pyproject.toml" "$INSTALL_DIR/backend/"; }
rsync -a --delete "$REPO_ROOT/frontend/dist/" "$INSTALL_DIR/frontend/dist/" 2>/dev/null \
  || { mkdir -p "$INSTALL_DIR/frontend/dist"; cp -r "$REPO_ROOT/frontend/dist/." "$INSTALL_DIR/frontend/dist/"; }
[ -f "$REPO_ROOT/VERSION" ] && cp "$REPO_ROOT/VERSION" "$INSTALL_DIR/VERSION"

# Seed the starter wallpaper pack only if there's nothing there yet — never
# overwrite wallpapers a user has already added or replaced.
if [ -d "$REPO_ROOT/wallpapers" ] && [ -z "$(ls -A "$CONFIG_DIR/wallpapers" 2>/dev/null)" ]; then
  log "Seeding the starter wallpaper pack"
  mkdir -p "$CONFIG_DIR/wallpapers"
  cp "$REPO_ROOT"/wallpapers/*.jpg "$CONFIG_DIR/wallpapers/" 2>/dev/null || true
fi

log "Installing the backend virtualenv"
[ -d "$INSTALL_DIR/.venv" ] || python3 -m venv "$INSTALL_DIR/.venv"
"$INSTALL_DIR/.venv/bin/pip" install -q --upgrade -e "$INSTALL_DIR/backend"

log "Installing the session script, hotkeys and recovery command"
backup /usr/local/bin/tv-home-session
sudo install -m 755 "$SCRIPT_DIR/tv-home-session.sh" /usr/local/bin/tv-home-session
mkdir -p "$HOME/.local/bin"
install -m 755 "$SCRIPT_DIR/tv-home-recover.sh" "$HOME/.local/bin/tv-home-recover"
install -m 644 "$SCRIPT_DIR/xbindkeysrc" "$CONFIG_DIR/xbindkeysrc"

log "Installing the xsession entry"
backup /usr/share/xsessions/tv-home.desktop
sudo install -m 644 "$SCRIPT_DIR/tv-home.desktop" /usr/share/xsessions/tv-home.desktop

log "Installing the systemd user unit"
mkdir -p "$HOME/.config/systemd/user"
install -m 644 "$SCRIPT_DIR/systemd/tv-home-backend.service" "$HOME/.config/systemd/user/tv-home-backend.service"
systemctl --user daemon-reload

log "Installing the polkit rule for passwordless sleep/restart/shut down"
install_polkit_rule

if systemctl --user is-active --quiet tv-home-backend.service 2>/dev/null; then
  log "Restarting the backend with the new version"
  systemctl --user restart tv-home-backend.service
fi

if $FROM_RELEASE; then
  log "Update complete ($(cat "$INSTALL_DIR/VERSION" 2>/dev/null || echo "unknown version"))."
  exit 0
fi

configure_autologin

cat <<EOF

TV Home 2.0 is installed. If you didn't enable autologin just now, pick
"TV Home" from the session chooser on the login screen to try it — see
session/README.md to turn autologin on (or off) later, or run
"$0 --check" any time to see its current status.
EOF
