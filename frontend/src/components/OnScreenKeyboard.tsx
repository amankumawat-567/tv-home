import type { ComponentChildren } from "preact";
import { useEffect, useRef, useState } from "preact/hooks";
import { useFocusable } from "../focus/useFocusable";
import { popScope, pushScope } from "../focus/engine";
import { onNav } from "../focus/navEvents";
import { api } from "../api";
import { BackspaceIcon, EyeIcon, PhoneIcon } from "./Icons";
import { QrCode } from "./QrCode";

const ROWS_LETTERS = ["1234567890", "qwertyuiop", "asdfghjkl", "zxcvbnm,./"];
const ROWS_SYMBOLS = ["!@#$%^&*()", "-_=+[]{}\\|", ";:'\"<>", "?/~`     "];
const PHONE_POLL_MS = 600;

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
  const [phoneToken, setPhoneToken] = useState<string | null>(null);
  const [phoneUrl, setPhoneUrl] = useState<string | null>(null);
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
    // the keyboard has focus. While phone-typing, Back just cancels that
    // instead (a tap wouldn't mean anything — there's no grid to delete from).
    const offBack = onNav("back", () => {
      if (phoneToken) {
        endPhoneSession();
      } else {
        backspace();
      }
      return true;
    });
    const offHoldBack = onNav("holdBack", () => {
      if (phoneToken) endPhoneSession();
      onCancel();
      return true;
    });
    return () => {
      offBack();
      offHoldBack();
    };
  }, [onCancel, phoneToken]);

  const endPhoneSession = () => {
    if (phoneToken) void api.endPhoneType(phoneToken).catch(() => undefined);
    setPhoneToken(null);
    setPhoneUrl(null);
  };

  const startPhoneTyping = async () => {
    const result = await api.startPhoneType().catch(() => null);
    if (!result) return;
    setPhoneToken(result.token);
    setPhoneUrl(result.url);
  };

  // I2: scan a QR code, type on your phone instead of hunting across this
  // grid — poll the session while it's open and submit the moment the phone
  // taps Done, same as pressing this keyboard's own Done would.
  useEffect(() => {
    if (!phoneToken) return;
    const id = window.setInterval(async () => {
      const session = await api.pollPhoneType(phoneToken).catch(() => null);
      if (!session) return;
      setValue(session.value);
      if (session.done) {
        window.clearInterval(id);
        void api.endPhoneType(phoneToken).catch(() => undefined);
        onSubmit(session.value);
      }
    }, PHONE_POLL_MS);
    return () => window.clearInterval(id);
  }, [phoneToken, onSubmit]);

  const rows = symbols ? ROWS_SYMBOLS : ROWS_LETTERS;
  const display = secure ? (reveal ? value.slice(0, -1).replace(/./g, "•") + value.slice(-1) : "•".repeat(value.length)) : value;

  return (
    <div className="keyboard-overlay">
      <div className="keyboard-field-row">
        <span className="keyboard-label">{label}</span>
        <div className="keyboard-field">
          <span className="keyboard-value">{display || <span className="keyboard-placeholder">—</span>}</span>
          {secure && <RevealToggle revealed={reveal} onToggle={() => setReveal((r) => !r)} />}
        </div>
        {!phoneToken && <PhoneButton onSelect={() => void startPhoneTyping()} />}
      </div>

      {phoneToken && phoneUrl ? (
        <div className="keyboard-phone">
          <QrCode value={phoneUrl} />
          <p className="dialog-message">Scan with your phone's camera, then type there — it appears here as you go.</p>
          <Key label="Cancel" wide rowGroup="kbrow-phone" onSelect={endPhoneSession} />
        </div>
      ) : (
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
      )}
    </div>
  );
}

function PhoneButton({ onSelect }: { onSelect: () => void }) {
  const { ref, focused } = useFocusable({ scope: "keyboard", onSelect });
  return (
    <button ref={ref as never} className={`keyboard-reveal focusable${focused ? " is-focused" : ""}`} onClick={onSelect} aria-label="Type on your phone">
      <PhoneIcon size={20} />
    </button>
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
