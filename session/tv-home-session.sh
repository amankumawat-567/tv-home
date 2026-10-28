#!/usr/bin/env bash
# TV Home 2.0's X11 session: the compositor, global hotkeys, the backend
# (via systemd --user), and a Chrome kiosk window pointed at it — restarted on
# crash, falling back to the regular desktop after repeated failures (Y2) or
# when told to via the "go-desktop" sentinel (Power > Go to desktop, or
# Ctrl+Alt+D's recovery script). Installed as the Exec= target of
# tv-home.desktop by install.sh.
#
# NOT RUNNABLE on this macOS dev sandbox — needs X11, xfwm4, xbindkeys,
# systemd --user and a real Chrome on PATH. Written to the PRD's own
# "Done when" checks (M5): verify on the real PC with 10 cold boots and by
# killing the shell 3 times to confirm the desktop fallback.
set -u

APPDIR="$HOME/.config/tv-home"
SENTINEL="$APPDIR/go-desktop"
BACKEND_URL="http://127.0.0.1:8000"
CRASH_WINDOW_SECONDS=300
CRASH_LIMIT=3

mkdir -p "$APPDIR"
log() { echo "[tv-home-session] $*" >&2; }

to_desktop() {
  log "Falling back to the regular desktop: $1"
  rm -f "$SENTINEL"
  systemctl --user stop tv-home-backend.service 2>/dev/null
  pkill -f "\-\-kiosk.*127\.0\.0\.1:8000" 2>/dev/null
  exec startxfce4
}

wait_for_backend() {
  for _ in $(seq 1 50); do
    curl -fs -o /dev/null "$BACKEND_URL/api/state" && return 0
    sleep 0.2
  done
  return 1
}

find_chrome() {
  for name in google-chrome google-chrome-stable chromium chromium-browser; do
    command -v "$name" && return 0
  done
  return 1
}

# xfwm4's compositor must stay ON — turning it off produced a black Chrome
# window on this hardware's Intel GPU (see the PRD's constraints).
xfwm4 --compositor=on --sm-client-disable &
xsetroot -solid "#101418" 2>/dev/null
xbindkeys -f "$APPDIR/xbindkeysrc" &

CHROME="$(find_chrome)"
if [ -z "$CHROME" ]; then
  to_desktop "Google Chrome isn't installed"
fi

crash_times=()
while true; do
  now=$(date +%s)
  crash_times=($(for t in "${crash_times[@]:-}"; do [ -n "$t" ] && [ $((now - t)) -lt $CRASH_WINDOW_SECONDS ] && echo "$t"; done))
  if [ "${#crash_times[@]}" -ge "$CRASH_LIMIT" ]; then
    to_desktop "$CRASH_LIMIT crashes within ${CRASH_WINDOW_SECONDS}s"
  fi

  systemctl --user restart tv-home-backend.service
  if ! wait_for_backend; then
    log "Backend didn't come up in time"
    crash_times+=("$now")
    sleep 1
    continue
  fi

  "$CHROME" --kiosk --password-store=basic \
    --user-data-dir="$APPDIR/chrome-profile" --no-first-run \
    --no-default-browser-check --disable-translate --disable-extensions \
    --disable-background-networking --disable-features=Translate \
    "$BACKEND_URL/"
  log "Chrome kiosk window exited"

  if [ -f "$SENTINEL" ]; then
    to_desktop "go-desktop requested"
  fi

  crash_times+=("$now")
  sleep 1
done
