// In-house spatial navigation: every focusable element on screen registers its
// DOM node; arrow keys pick the nearest neighbour in that direction by comparing
// edge gaps, the same heuristic browsers use for CSS spatial navigation. Chosen
// over a library (e.g. Norigin Spatial Navigation) to keep the bundle small —
// see the PRD's stack table, which offers both.
import { signal } from "@preact/signals";

export type Direction = "up" | "down" | "left" | "right";

interface Entry {
  id: string;
  el: HTMLElement;
  scope: string; // which focus scope this element belongs to (see pushScope/popScope)
  wrapGroup?: string; // elements that should wrap around at the row/column edge
  onSelect?: () => void;
}

const registry = new Map<string, Entry>();

// A stack of scopes: only the top scope's elements are reachable by arrow keys.
// Opening a panel pushes a new scope and remembers which element had focus so
// Back can restore it exactly, per the PRD's navigation rule ("focus returns to
// whatever opened a panel").
interface ScopeFrame {
  scope: string;
  returnTo: string | null;
}
const scopeStack: ScopeFrame[] = [{ scope: "root", returnTo: null }];

export const focusedId = signal<string | null>(null);
export const currentScope = signal<string>("root");

export function register(entry: Entry) {
  registry.set(entry.id, entry);
  if (focusedId.value === null && entry.scope === currentScope.value) {
    focusedId.value = entry.id;
  }
}

export function unregister(id: string) {
  registry.delete(id);
  if (focusedId.value === id) {
    focusedId.value = firstInScope(currentScope.value);
  }
}

function firstInScope(scope: string): string | null {
  for (const e of registry.values()) if (e.scope === scope) return e.id;
  return null;
}

export function pushScope(scope: string) {
  scopeStack.push({ scope, returnTo: focusedId.value });
  currentScope.value = scope;
  focusedId.value = firstInScope(scope);
}

export function popScope(): string | null {
  if (scopeStack.length <= 1) return null;
  const frame = scopeStack.pop()!;
  const parent = scopeStack[scopeStack.length - 1];
  currentScope.value = parent.scope;
  focusedId.value = frame.returnTo && registry.has(frame.returnTo) ? frame.returnTo : firstInScope(parent.scope);
  return frame.scope;
}

export function setFocus(id: string) {
  const entry = registry.get(id);
  if (!entry) return;
  focusedId.value = id;
  entry.el.scrollIntoView({ block: "nearest", inline: "nearest" });
}

export function activate() {
  const id = focusedId.value;
  if (!id) return;
  registry.get(id)?.onSelect?.();
}

function rectOf(el: HTMLElement): DOMRect {
  return el.getBoundingClientRect();
}

/** Lower is better. Primary = distance along the travel axis; perpendicular
 * offset is weighted higher so same-row/column neighbours win over diagonal ones. */
function score(dir: Direction, from: DOMRect, to: DOMRect): number | null {
  const PERP_WEIGHT = 2;
  switch (dir) {
    case "right": {
      if (to.left < from.right - 1) return null;
      const primary = Math.max(0, to.left - from.right);
      const perp = Math.abs((to.top + to.bottom) / 2 - (from.top + from.bottom) / 2);
      return primary + perp * PERP_WEIGHT;
    }
    case "left": {
      if (to.right > from.left + 1) return null;
      const primary = Math.max(0, from.left - to.right);
      const perp = Math.abs((to.top + to.bottom) / 2 - (from.top + from.bottom) / 2);
      return primary + perp * PERP_WEIGHT;
    }
    case "down": {
      if (to.top < from.bottom - 1) return null;
      const primary = Math.max(0, to.top - from.bottom);
      const perp = Math.abs((to.left + to.right) / 2 - (from.left + from.right) / 2);
      return primary + perp * PERP_WEIGHT;
    }
    case "up": {
      if (to.bottom > from.top + 1) return null;
      const primary = Math.max(0, from.top - to.bottom);
      const perp = Math.abs((to.left + to.right) / 2 - (from.left + from.right) / 2);
      return primary + perp * PERP_WEIGHT;
    }
  }
}

function candidatesInScope(scope: string, excludeId: string): Entry[] {
  return [...registry.values()].filter((e) => e.scope === scope && e.id !== excludeId);
}

/** Wrap fallback: among elements sharing the moving element's wrapGroup, jump to
 * the one furthest in the opposite direction (same row wraps left<->right, etc). */
function wrapCandidate(dir: Direction, current: Entry): Entry | null {
  if (!current.wrapGroup) return null;
  const siblings = [...registry.values()].filter(
    (e) => e.scope === current.scope && e.wrapGroup === current.wrapGroup && e.id !== current.id,
  );
  if (siblings.length === 0) return null;
  const axis = dir === "left" || dir === "right" ? "x" : "y";
  const pick = (want: "min" | "max") =>
    siblings.reduce((best, e) => {
      const r = rectOf(e.el);
      const v = axis === "x" ? (r.left + r.right) / 2 : (r.top + r.bottom) / 2;
      const br = rectOf(best.el);
      const bv = axis === "x" ? (br.left + br.right) / 2 : (br.top + br.bottom) / 2;
      return want === "min" ? (v < bv ? e : best) : v > bv ? e : best;
    });
  if (dir === "right") return pick("min");
  if (dir === "left") return pick("max");
  if (dir === "down") return pick("min");
  return pick("max");
}

export function move(dir: Direction) {
  const id = focusedId.value;
  if (!id) {
    const first = firstInScope(currentScope.value);
    if (first) focusedId.value = first;
    return;
  }
  const current = registry.get(id);
  if (!current) return;
  const fromRect = rectOf(current.el);

  let best: Entry | null = null;
  let bestScore = Infinity;
  for (const cand of candidatesInScope(current.scope, id)) {
    const s = score(dir, fromRect, rectOf(cand.el));
    if (s !== null && s < bestScore) {
      bestScore = s;
      best = cand;
    }
  }
  best ??= wrapCandidate(dir, current);
  if (best) setFocus(best.id);
}

export function focusedEntry(): Entry | undefined {
  const id = focusedId.value;
  return id ? registry.get(id) : undefined;
}
