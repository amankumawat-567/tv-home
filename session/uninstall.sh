#!/usr/bin/env bash
# Reverses install.sh: stops and removes the systemd unit, the session script,
# the xsession entry and the recovery command, restoring any backup install.sh
# made along the way. Leaves ~/.config/tv-home (your apps, settings, icons)
# and ~/.local/share/tv-home (the installed app itself) in place unless you
# pass --purge.
#
# NOT RUNNABLE on this macOS dev sandbox — see session/install.sh.
set -euo pipefail

CONFIG_DIR="$HOME/.config/tv-home"
INSTALL_DIR="$HOME/.local/share/tv-home"
LIGHTDM_CONF=/etc/lightdm/lightdm.conf.d/50-tv-home.conf
PURGE=false
[ "${1:-}" = "--purge" ] && PURGE=true

log() { echo "==> $*"; }

restore_or_remove() {
  local path="$1"
  if [ -e "$path.tv-home-orig" ]; then
    sudo mv "$path.tv-home-orig" "$path" 2>/dev/null || mv "$path.tv-home-orig" "$path"
    log "Restored $path"
  else
    sudo rm -f "$path" 2>/dev/null || rm -f "$path"
    log "Removed $path"
  fi
}

log "Stopping the backend"
systemctl --user stop tv-home-backend.service 2>/dev/null || true
systemctl --user disable tv-home-backend.service 2>/dev/null || true
rm -f "$HOME/.config/systemd/user/tv-home-backend.service"
systemctl --user daemon-reload 2>/dev/null || true

restore_or_remove /usr/local/bin/tv-home-session
restore_or_remove /usr/share/xsessions/tv-home.desktop
rm -f "$HOME/.local/bin/tv-home-recover"
rm -f "$CONFIG_DIR/xbindkeysrc"

if [ -e "$LIGHTDM_CONF" ]; then
  sudo rm -f "$LIGHTDM_CONF" 2>/dev/null || rm -f "$LIGHTDM_CONF"
  log "Removed autologin ($LIGHTDM_CONF) — the login screen will ask again next boot"
fi

if $PURGE; then
  log "Removing $INSTALL_DIR and $CONFIG_DIR (--purge)"
  rm -rf "$INSTALL_DIR" "$CONFIG_DIR"
else
  log "Kept $INSTALL_DIR and $CONFIG_DIR — pass --purge to remove your apps/settings too"
fi

cat <<'EOF'

TV Home 2.0 is uninstalled. Reboot for the login screen to go back to normal.
EOF
