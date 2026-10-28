// Semantic remote actions, decoupled from the physical keys that trigger them
// (see useKeyNav). Screens/panels subscribe to the ones they care about instead
// of each owning a keydown listener.
export type NavAction =
  | "select"
  | "holdSelect"
  | "back"
  | "holdBack"
  | "home"
  | "holdHome"
  | "menu"
  | "volumeUp"
  | "volumeDown"
  | "volumeMute"
  | "recoveryDesktop";

type Listener = () => boolean | void; // return true to mark the event handled (stops at this listener)

const listeners: Record<NavAction, Listener[]> = {
  select: [],
  holdSelect: [],
  back: [],
  holdBack: [],
  home: [],
  holdHome: [],
  menu: [],
  volumeUp: [],
  volumeDown: [],
  volumeMute: [],
  recoveryDesktop: [],
};

/** Subscribe; listeners fire most-recently-subscribed first, so a panel pushed
 * on top of Home handles `back`/`home` before Home's own top-level handler does. */
export function onNav(action: NavAction, fn: Listener): () => void {
  listeners[action].unshift(fn);
  return () => {
    const i = listeners[action].indexOf(fn);
    if (i >= 0) listeners[action].splice(i, 1);
  };
}

export function emitNav(action: NavAction) {
  for (const fn of listeners[action]) {
    if (fn() === true) return;
  }
}
