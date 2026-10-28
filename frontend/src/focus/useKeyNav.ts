import { useEffect, useRef } from "preact/hooks";
import { move, activate } from "./engine";
import { emitNav } from "./navEvents";

const HOLD_MS = 600;

type HoldKey = "select" | "home" | "back";

/** Maps the PRD's key map table to focus-engine moves and semantic nav events.
 * Global keys (Home, volume, recovery) are meant to be grabbed at the X11 level
 * on the real PC (see session/xbindkeysrc) so they work over a running app too;
 * this listener is what drives them inside the TV Home UI itself.
 *
 * Select and Home distinguish a tap from a 600ms hold (tile options / quick
 * settings vs. select / go home). Back normally just fires on tap ("go up one
 * level"); the on-screen keyboard additionally listens for a *held* Back to
 * mean "close the keyboard" while a tap deletes one character — see
 * components/OnScreenKeyboard, which subscribes to "back" itself and only lets
 * a long-press escalate via the "holdBack" event below. */
export function useKeyNav() {
  const timers = useRef<Record<HoldKey, number | undefined>>({ select: undefined, home: undefined, back: undefined });
  const fired = useRef<Record<HoldKey, boolean>>({ select: false, home: false, back: false });

  useEffect(() => {
    const isHome = (k: string) => k === "Home" || k === "F12" || k === "XF86HomePage";
    const isBack = (k: string) => k === "Escape" || k === "Backspace" || k === "XF86Back" || k === "BrowserBack";
    const isSelect = (k: string) => k === "Enter" || k === " ";
    const isMenu = (k: string) => k === "ContextMenu" || k.toLowerCase() === "m";

    const startHold = (key: HoldKey, onHold: () => void) => {
      if (fired.current[key]) return;
      window.clearTimeout(timers.current[key]);
      timers.current[key] = window.setTimeout(() => {
        fired.current[key] = true;
        onHold();
      }, HOLD_MS);
    };

    const endHold = (key: HoldKey, onTap: () => void) => {
      window.clearTimeout(timers.current[key]);
      const held = fired.current[key];
      fired.current[key] = false;
      if (!held) onTap();
    };

    const onKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const typing = target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA");

      switch (e.key) {
        case "ArrowUp":
          e.preventDefault();
          move("up");
          return;
        case "ArrowDown":
          e.preventDefault();
          move("down");
          return;
        case "ArrowLeft":
          if (typing) return;
          e.preventDefault();
          move("left");
          return;
        case "ArrowRight":
          if (typing) return;
          e.preventDefault();
          move("right");
          return;
        case "AudioVolumeUp":
        case "XF86AudioRaiseVolume":
          emitNav("volumeUp");
          return;
        case "AudioVolumeDown":
        case "XF86AudioLowerVolume":
          emitNav("volumeDown");
          return;
        case "AudioVolumeMute":
        case "XF86AudioMute":
          emitNav("volumeMute");
          return;
      }

      if (isSelect(e.key) && !typing) {
        e.preventDefault();
        startHold("select", () => emitNav("holdSelect"));
        return;
      }
      if (isHome(e.key)) {
        e.preventDefault();
        startHold("home", () => emitNav("holdHome"));
        return;
      }
      if (isBack(e.key) && !typing) {
        e.preventDefault();
        startHold("back", () => emitNav("holdBack"));
        return;
      }
      if (isMenu(e.key)) {
        e.preventDefault();
        emitNav("menu");
        return;
      }
      if (e.ctrlKey && e.altKey && e.key.toLowerCase() === "d") {
        e.preventDefault();
        emitNav("recoveryDesktop");
      }
    };

    const onKeyUp = (e: KeyboardEvent) => {
      if (isSelect(e.key)) endHold("select", activate);
      else if (isHome(e.key)) endHold("home", () => emitNav("home"));
      else if (isBack(e.key)) endHold("back", () => emitNav("back"));
    };

    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup", onKeyUp);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("keyup", onKeyUp);
    };
  }, []);
}
