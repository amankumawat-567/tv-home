#!/usr/bin/env bash
# Ctrl+Alt+D's recovery action (Y3: "always reaches the desktop"). Deliberately
# does not depend on the backend responding — it works even if TV Home has
# crashed outright. Installed to ~/.local/bin/tv-home-recover by install.sh.
set -u

mkdir -p "$HOME/.config/tv-home"
touch "$HOME/.config/tv-home/go-desktop"
systemctl --user stop tv-home-backend.service 2>/dev/null
pkill -f "\-\-kiosk.*127\.0\.0\.1:8000" 2>/dev/null
pkill -f tv-home-session 2>/dev/null
exec startxfce4
