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
# written to spec; run and verify on the real PC. See session/README.md for
# the manual step this intentionally leaves to you (enabling autologin).
set -euo pipefail

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

cat <<EOF

TV Home 2.0 is installed.

One manual step remains on purpose — enabling autologin into this session
touches LightDM's config for every user on this machine, so it's not done
automatically. See session/README.md for the one-line snippet to add under
/etc/lightdm/lightdm.conf.d/.

Until then, you can pick "TV Home" from the session chooser on the login
screen to try it.
EOF
