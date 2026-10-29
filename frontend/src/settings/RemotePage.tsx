import { useEffect, useState } from "preact/hooks";
import { api } from "../api";
import { pushToast } from "../state/data";
import { ACTIONS, defaultKeysFor, overrides, type KeyAction } from "../state/keymap";
import { SettingsRow } from "../components/SettingsRow";

const LABELS: Record<KeyAction, string> = {
  up: "Up",
  down: "Down",
  left: "Left",
  right: "Right",
  select: "OK / Select",
  back: "Back",
  home: "Home",
  menu: "Menu",
};

// A short, readable name for the keys a real remote or keyboard actually
// sends — the raw KeyboardEvent.key values are fine functionally but not
// worth showing verbatim (e.g. "XF86HomePage" wouldn't mean anything here).
const FRIENDLY: Record<string, string> = {
  ArrowUp: "Up arrow",
  ArrowDown: "Down arrow",
  ArrowLeft: "Left arrow",
  ArrowRight: "Right arrow",
  Enter: "Enter",
  " ": "Space",
  Escape: "Esc",
  Backspace: "Backspace",
  XF86Back: "Back button",
  BrowserBack: "Back button",
  Home: "Home button",
  F12: "F12",
  XF86HomePage: "Home button",
  ContextMenu: "Menu button",
};

function describe(key: string): string {
  return FRIENDLY[key] ?? (key.length === 1 ? key.toUpperCase() : key);
}

function defaultLabel(action: KeyAction): string {
  return defaultKeysFor(action).map(describe).join(" / ");
}

export function RemotePage() {
  const [learning, setLearning] = useState<KeyAction | null>(null);

  useEffect(() => {
    if (!learning) return;
    const onKeyDown = (e: KeyboardEvent) => {
      e.preventDefault();
      e.stopImmediatePropagation();
      if (e.key === "Escape") {
        setLearning(null);
        return;
      }
      const action = learning;
      setLearning(null);
      void api
        .setKeymapKey(action, e.key)
        .then((map) => {
          overrides.value = map;
          pushToast(`${LABELS[action]} set to ${describe(e.key)}.`, "good");
        })
        .catch(() => pushToast("Couldn't save that — try again.", "bad"));
    };
    // Capture phase, ahead of useKeyNav's own (bubble-phase) listener, so the
    // key being learned never also moves focus or triggers its old action.
    window.addEventListener("keydown", onKeyDown, { capture: true });
    return () => window.removeEventListener("keydown", onKeyDown, { capture: true });
  }, [learning]);

  const reset = async () => {
    const map = await api.resetKeymap().catch(() => null);
    if (map) {
      overrides.value = map;
      pushToast("Remote keys reset to defaults.", "good");
    }
  };

  return (
    <div className="settings-page">
      <h1 className="settings-title">Remote</h1>
      <p className="dialog-message">
        Using an unusual remote? Select a button below, then press the one on your remote you want to use for it.
      </p>
      {ACTIONS.map((action) => {
        const custom = overrides.value[action];
        return (
          <SettingsRow
            key={action}
            label={LABELS[action]}
            value={learning === action ? `Press a button… (Esc to cancel)` : custom ? describe(custom) : defaultLabel(action)}
            onSelect={() => setLearning(action)}
          />
        );
      })}
      <SettingsRow label="Reset all to defaults" danger onSelect={reset} />
    </div>
  );
}
