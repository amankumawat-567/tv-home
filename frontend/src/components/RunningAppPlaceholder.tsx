// On the real PC the launched app is a separate full-screen Chrome kiosk
// window that physically covers this one — the backend's `launch`/`home`
// endpoints just spawn/kill that process (see backend/tv_home/chrome.py).
// This placeholder only matters for development here, where there's no
// window manager to hand focus to a second window, so M2's "launch/close 10x"
// check has something on screen to verify against.
import { runningApp } from "../state/data";

export function RunningAppPlaceholder() {
  const app = runningApp.value;
  if (!app) return null;
  return (
    <div className="running-app-placeholder">
      <div className="running-app-name">{app.name}</div>
      <div className="running-app-hint">(standing in for a separate Chrome kiosk window) — press Home to return</div>
    </div>
  );
}
