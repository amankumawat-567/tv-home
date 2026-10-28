import { useEffect } from "preact/hooks";
import { screensaverActive, quickSettingsOpen, appStoreOpen } from "../state/ui";
import { Clock, longDate } from "./Clock";

const IDLE_MS = 10 * 60 * 1000; // "Screensaver after 10 minutes idle on Home" (H7)

export function useScreensaver() {
  useEffect(() => {
    let timer: number;
    const arm = () => {
      window.clearTimeout(timer);
      if (screensaverActive.value) screensaverActive.value = false;
      // Only idle-times-out on Home with nothing else open, per the PRD (H7 is a
      // Home requirement; a settings panel or the App Store shouldn't dim away).
      if (quickSettingsOpen.value || appStoreOpen.value) return;
      timer = window.setTimeout(() => (screensaverActive.value = true), IDLE_MS);
    };
    const events = ["keydown", "mousemove", "pointerdown"];
    events.forEach((e) => window.addEventListener(e, arm));
    arm();
    return () => {
      window.clearTimeout(timer);
      events.forEach((e) => window.removeEventListener(e, arm));
    };
  }, []);
}

export function Screensaver() {
  if (!screensaverActive.value) return null;
  return (
    <div className="screensaver" onClick={() => (screensaverActive.value = false)}>
      <Clock className="screensaver-clock" />
      <div className="screensaver-date">{longDate()}</div>
    </div>
  );
}
