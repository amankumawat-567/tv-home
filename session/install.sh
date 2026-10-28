#!/usr/bin/env bash
# Installs (or updates) TV Home 2.0 onto a Xubuntu PC: puts the frontend and
# backend into ~/.local/share/tv-home, installs the X11 session, global
# hotkeys, the systemd user unit, and the recovery script. Backs up any
# system file it touches before changing it (Y5).
#
# From a source checkout (builds the frontend here — needs node/npm):
#   ./session/install.sh
#
# From a downloaded release (ships a prebuilt frontend/dist — no node/npm
# needed; this is also how the backend's own self-update, Y6, re-installs):
#   ./session/install.sh --from-release /path/to/extracted/release
#
# NOT RUNNABLE on this macOS dev sandbox (needs apt, systemd, LightDM, X11) —
# written to spec; run and verify on the real PC. On a fresh interactive
# install it offers to enable autologin into this session (skipped entirely
# on an update, non-interactive run, or a machine with no LightDM) — see
# configure_autologin() below and session/README.md.
set -euo pipefail

LIGHTDM_CONF=/etc/lightdm/lightdm.conf.d/50-tv-home.conf

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/.local/share/tv-home"
CONFIG_DIR="$HOME/.config/tv-home"
FROM_RELEASE=false

if [ "${1:-}" = "--from-release" ]; then
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
  if [ ! -t 0 ]; then
    log "Non-interactive run — skipping the autologin prompt (see session/README.md to enable it later)"
    return
  fi

  read -r -p "==> Enable autologin straight into TV Home on boot? [y/N] " reply
  case "$reply" in
    [Yy]*) ;;
    *) log "Skipped autologin — pick \"TV Home\" manually at the login screen, or re-run this script later"; return ;;
  esac
  read -r -p "==> Autologin as which user? [$USER] " autologin_user
  autologin_user="${autologin_user:-$USER}"
  id "$autologin_user" >/dev/null 2>&1 || { echo "No such user: $autologin_user — skipping autologin." >&2; return; }

  sudo mkdir -p "$(dirname "$LIGHTDM_CONF")"
  printf '[Seat:*]\nautologin-user=%s\nautologin-session=tv-home\n' "$autologin_user" | sudo tee "$LIGHTDM_CONF" >/dev/null
  log "Autologin enabled for $autologin_user — reboot to try it (remove $LIGHTDM_CONF to undo, or run session/uninstall.sh)"
}

log "Checking prerequisites"
if command -v apt-get >/dev/null; then
  sudo apt-get update -qq
  sudo apt-get install -y -qq python3-venv python3-pip xbindkeys curl rsync >/dev/null
else
  log "apt-get not found — make sure python3-venv, xbindkeys, curl and rsync are installed"
fi
command -v python3 >/dev/null || { echo "Missing required command: python3" >&2; exit 1; }

if $FROM_RELEASE; then
  [ -d "$REPO_ROOT/frontend/dist" ] || { echo "No prebuilt frontend/dist in $REPO_ROOT — is this a release tarball?" >&2; exit 1; }
  log "Using the prebuilt frontend from the release (no build needed)"
else
  for bin in node npm; do
    command -v "$bin" >/dev/null || { echo "Missing required command: $bin (only needed when building from source)" >&2; exit 1; }
  done
  log "Building the frontend"
  (cd "$REPO_ROOT/frontend" && npm install && npm run build)
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
session/README.md to turn autologin on (or off) later.
EOF
