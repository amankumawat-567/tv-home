import type { ComponentChildren } from "preact";
import { useEffect, useRef, useState } from "preact/hooks";
import { useFocusable } from "../focus/useFocusable";
import { popScope, pushScope } from "../focus/engine";
import { onNav } from "../focus/navEvents";
import { BackspaceIcon, EyeIcon } from "./Icons";

const ROWS_LETTERS = ["1234567890", "qwertyuiop", "asdfghjkl", "zxcvbnm,./"];
const ROWS_SYMBOLS = ["!@#$%^&*()", "-_=+[]{}\\|", ";:'\"<>", "?/~`     "];

export interface OnScreenKeyboardProps {
  label: string;
  initialValue?: string;
  secure?: boolean;
  submitLabel?: string;
  onSubmit: (value: string) => void;
  onCancel: () => void;
}

export function OnScreenKeyboard({ label, initialValue = "", secure, submitLabel = "Done", onSubmit, onCancel }: OnScreenKeyboardProps) {
  const [value, setValue] = useState(initialValue);
  const [shift, setShift] = useState(false);
  const [symbols, setSymbols] = useState(false);
  const [reveal, setReveal] = useState(false);
  const revealTimer = useRef<number | undefined>(undefined);

  useEffect(() => {
    pushScope("keyboard");
    return () => popScope();
  }, []);

  const typeChar = (raw: string) => {
    const ch = shift && !symbols ? raw.toUpperCase() : raw;
    setValue((v) => v + ch);
    if (secure) {
      setReveal(true);
      window.clearTimeout(revealTimer.current);
      revealTimer.current = window.setTimeout(() => setReveal(false), 1000);
    }
    if (shift) setShift(false);
  };

  const backspace = () => setValue((v) => v.slice(0, -1));

  useEffect(() => {
    // Back (tap) deletes a character instead of closing a panel; holding Back
    // closes the keyboard — the PRD's own remapping of the Back button while
    // the keyboard has focus.
    const offBack = onNav("back", () => {
      backspace();
      return true;
    });
    const offHoldBack = onNav("holdBack", () => {
      onCancel();
      return true;
    });
    return () => {
      offBack();
      offHoldBack();
    };
  }, [onCancel]);

  const rows = symbols ? ROWS_SYMBOLS : ROWS_LETTERS;
  const display = secure ? (reveal ? value.slice(0, -1).replace(/./g, "•") + value.slice(-1) : "•".repeat(value.length)) : value;

  return (
    <div className="keyboard-overlay">
      <div className="keyboard-field-row">
        <span className="keyboard-label">{label}</span>
        <div className="keyboard-field">
          <span className="keyboard-value">{display || <span className="keyboard-placeholder">—</span>}</span>
          {secure && (
            <RevealToggle revealed={reveal} onToggle={() => setReveal((r) => !r)} />
          )}
        </div>
      </div>
      <div className="keyboard-rows">
        {rows.map((row, ri) => (
          <div className="keyboard-row" key={ri}>
            {[...row].map((ch, ci) => (
              <Key key={`${ri}-${ci}`} label={shift && !symbols ? ch.toUpperCase() : ch} rowGroup={`kbrow-${ri}`} onSelect={() => typeChar(ch)} />
            ))}
          </div>
        ))}
        <div className="keyboard-row keyboard-row-bottom">
          <Key label={symbols ? "ABC" : "123"} wide rowGroup="kbrow-bottom" onSelect={() => setSymbols((s) => !s)} />
          <Key label="Shift" wide active={shift} rowGroup="kbrow-bottom" onSelect={() => setShift((s) => !s)} disabled={symbols} />
          <Key label="Space" widest rowGroup="kbrow-bottom" onSelect={() => typeChar(" ")} />
          <Key label={<BackspaceIcon size={22} />} wide rowGroup="kbrow-bottom" onSelect={backspace} />
          <Key label={submitLabel} wide accent rowGroup="kbrow-bottom" onSelect={() => onSubmit(value)} />
        </div>
      </div>
    </div>
  );
}

function RevealToggle({ revealed, onToggle }: { revealed: boolean; onToggle: () => void }) {
  const { ref, focused } = useFocusable({ scope: "keyboard", onSelect: onToggle });
  return (
    <button ref={ref as never} className={`keyboard-reveal focusable${focused ? " is-focused" : ""}`} onClick={onToggle} aria-label="Show password">
      <EyeIcon open={revealed} size={20} />
    </button>
  );
}

function Key({
  label,
  onSelect,
  rowGroup,
  wide,
  widest,
  active,
  accent,
  disabled,
}: {
  label: ComponentChildren;
  onSelect: () => void;
  rowGroup: string;
  wide?: boolean;
  widest?: boolean;
  active?: boolean;
  accent?: boolean;
  disabled?: boolean;
}) {
  const { ref, focused } = useFocusable({ scope: "keyboard", wrapGroup: rowGroup, onSelect, disabled });
  const cls = [
    "keyboard-key",
    "focusable",
    focused && "is-focused",
    wide && "is-wide",
    widest && "is-widest",
    active && "is-active",
    accent && "is-accent",
    disabled && "is-disabled",
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <button ref={ref as never} className={cls} onClick={disabled ? undefined : onSelect}>
      {label}
    </button>
  );
}
