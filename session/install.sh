#!/usr/bin/env bash
# Installs TV Home 2.0 onto a Xubuntu PC: builds the frontend and backend into
# ~/.local/share/tv-home, installs the X11 session, global hotkeys, the
# systemd user unit, and the recovery script. Backs up any system file it
# touches before changing it (Y5). Run from a clone of this repo:
#
#   ./session/install.sh
#
# NOT RUNNABLE on this macOS dev sandbox (needs apt, systemd, LightDM, X11) —
# written to spec; run and verify on the real PC. See session/README.md for
# the manual step this intentionally leaves to you (enabling autologin).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
INSTALL_DIR="$HOME/.local/share/tv-home"
CONFIG_DIR="$HOME/.config/tv-home"

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
  sudo apt-get install -y -qq python3-venv python3-pip xbindkeys curl >/dev/null
else
  log "apt-get not found — make sure python3-venv, xbindkeys and curl are installed"
fi
for bin in python3 node npm; do
  command -v "$bin" >/dev/null || { echo "Missing required command: $bin" >&2; exit 1; }
done

log "Building the frontend"
(cd "$REPO_ROOT/frontend" && npm install && npm run build)

log "Installing to $INSTALL_DIR"
mkdir -p "$INSTALL_DIR" "$CONFIG_DIR"
rsync -a --delete "$REPO_ROOT/backend/tv_home" "$REPO_ROOT/backend/pyproject.toml" "$INSTALL_DIR/backend/" 2>/dev/null \
  || { mkdir -p "$INSTALL_DIR/backend"; cp -r "$REPO_ROOT/backend/tv_home" "$REPO_ROOT/backend/pyproject.toml" "$INSTALL_DIR/backend/"; }
rsync -a --delete "$REPO_ROOT/frontend/dist/" "$INSTALL_DIR/frontend/dist/" 2>/dev/null \
  || { mkdir -p "$INSTALL_DIR/frontend/dist"; cp -r "$REPO_ROOT/frontend/dist/." "$INSTALL_DIR/frontend/dist/"; }

log "Creating the backend virtualenv"
python3 -m venv "$INSTALL_DIR/.venv"
"$INSTALL_DIR/.venv/bin/pip" install -q -e "$INSTALL_DIR/backend"

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

cat <<EOF

TV Home 2.0 is installed.

One manual step remains on purpose — enabling autologin into this session
touches LightDM's config for every user on this machine, so it's not done
automatically. See session/README.md for the one-line snippet to add under
/etc/lightdm/lightdm.conf.d/.

Until then, you can pick "TV Home" from the session chooser on the login
screen to try it.
EOF
