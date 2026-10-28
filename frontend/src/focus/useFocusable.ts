import { useEffect, useRef } from "preact/hooks";
import { focusedId, register, unregister, setFocus, currentScope } from "./engine";

let counter = 0;

export interface UseFocusableOptions {
  scope?: string; // defaults to the currently active scope
  wrapGroup?: string;
  onSelect?: () => void;
  autoFocus?: boolean;
  disabled?: boolean;
}

/** Registers a DOM element as a focus-engine target. Returns a ref to attach to
 * the element and whether it currently holds focus (drive your CSS off this,
 * not :focus — these elements are never real DOM focus targets). */
export function useFocusable(opts: UseFocusableOptions = {}) {
  const idRef = useRef<string>(undefined);
  if (!idRef.current) idRef.current = `f${++counter}`;
  const id = idRef.current;
  const elRef = useRef<HTMLElement | null>(null);
  const scope = opts.scope ?? currentScope.value;

  // onSelect is read through a ref so the registry entry can stay a stable
  // closure without re-registering (and losing scroll/focus state) every time
  // the caller passes a fresh inline function.
  const onSelectRef = useRef(opts.onSelect);
  onSelectRef.current = opts.onSelect;

  useEffect(() => {
    if (opts.disabled) return;
    const el = elRef.current;
    if (!el) return;
    register({ id, el, scope, wrapGroup: opts.wrapGroup, onSelect: () => onSelectRef.current?.() });
    if (opts.autoFocus) setFocus(id);
    return () => unregister(id);
  }, [scope, opts.wrapGroup, opts.disabled]);

  return { ref: elRef, focused: focusedId.value === id, id };
}
