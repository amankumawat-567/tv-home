import { signal } from "@preact/signals";
import { api } from "../api";

export const ACTIONS = ["up", "down", "left", "right", "select", "back", "home", "menu"] as const;
export type KeyAction = (typeof ACTIONS)[number];
export type Keymap = Record<KeyAction, string | null>;

// Built-in fallbacks — what every remote/keyboard already does out of the box
// (see the PRD's key map table). A remapped action replaces this list
// entirely with the one physical key learned for it; an unmapped action
// keeps matching any of these, so remapping one button never breaks another.
const DEFAULTS: Record<KeyAction, string[]> = {
  up: ["ArrowUp"],
  down: ["ArrowDown"],
  left: ["ArrowLeft"],
  right: ["ArrowRight"],
  select: ["Enter", " "],
  back: ["Escape", "Backspace", "XF86Back", "BrowserBack"],
  home: ["Home", "F12", "XF86HomePage"],
  menu: ["ContextMenu"],
};

export const overrides = signal<Keymap>({
  up: null,
  down: null,
  left: null,
  right: null,
  select: null,
  back: null,
  home: null,
  menu: null,
});

export function matches(action: KeyAction, key: string): boolean {
  const override = overrides.value[action];
  if (override) return key === override;
  return DEFAULTS[action].includes(key);
}

export function defaultKeysFor(action: KeyAction): string[] {
  return DEFAULTS[action];
}

export async function loadKeymap(): Promise<void> {
  const map = await api.getKeymap().catch(() => null);
  if (map) overrides.value = map;
}
