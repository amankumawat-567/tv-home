import { useEffect, useRef, useState } from "preact/hooks";
import { api } from "../api";
import { pushToast } from "../state/data";
import { usePolling } from "../utils/usePolling";
import { popScope, pushScope } from "../focus/engine";
import { useFocusable } from "../focus/useFocusable";
import { SettingsRow } from "../components/SettingsRow";

const SCREEN_OFF_OPTIONS = [0, 5, 10, 15, 30];
const REVERT_SECONDS = 15;

function RevertButton({ label, onSelect, autoFocus }: { label: string; onSelect: () => void; autoFocus?: boolean }) {
  const { ref, focused } = useFocusable({ scope: "display-confirm", wrapGroup: "display-confirm-row", onSelect, autoFocus });
  return (
    <button ref={ref as never} className={`dialog-button focusable${focused ? " is-focused" : ""}`} onClick={onSelect}>
      {label}
    </button>
  );
}

function RevertConfirm({ onDone }: { onDone: (kept: boolean) => void }) {
  const [secondsLeft, setSecondsLeft] = useState(REVERT_SECONDS);

  useEffect(() => {
    pushScope("display-confirm");
    const id = setInterval(() => setSecondsLeft((s) => s - 1), 1000);
    return () => {
      clearInterval(id);
      popScope();
    };
  }, []);

  useEffect(() => {
    if (secondsLeft <= 0) onDone(false);
  }, [secondsLeft, onDone]);

  return (
    <div className="dialog-backdrop">
      <div className="dialog">
        <h2 className="dialog-title">Keep this resolution?</h2>
        <p className="dialog-message">Reverting in {secondsLeft}s if you don't confirm.</p>
        <div className="dialog-buttons">
          <RevertButton label="Revert" onSelect={() => onDone(false)} />
          <RevertButton label="Keep" autoFocus onSelect={() => onDone(true)} />
        </div>
      </div>
    </div>
  );
}

export function DisplayPage() {
  const { data, refresh } = usePolling(() => api.display(), 10000);
  const [pending, setPending] = useState<string | null>(null);
  const pendingRef = useRef<string | null>(null);

  if (!data) return <p className="settings-empty">Loading…</p>;
  if (!data.available) return <p className="settings-empty">{data.error ?? "Display settings aren't available on this PC."}</p>;

  const pick = async (id: string) => {
    const result = await api.displaySet(id).catch(() => null);
    if (!result?.ok) {
      pushToast("Couldn't change the resolution.", "bad");
      return;
    }
    pendingRef.current = result.token;
    setPending(result.token);
  };

  const finish = async (kept: boolean) => {
    if (kept && pendingRef.current) await api.displayConfirm(pendingRef.current).catch(() => undefined);
    pendingRef.current = null;
    setPending(null);
    refresh();
  };

  return (
    <div className="settings-page">
      <h1 className="settings-title">Display</h1>
      <h2 className="settings-subtitle">Resolution</h2>
      {data.modes.map((m) => (
        <SettingsRow key={m.id} label={m.label} value={m.current ? "Current" : undefined} onSelect={() => pick(m.id)} />
      ))}
      <h2 className="settings-subtitle">Screen off after</h2>
      {SCREEN_OFF_OPTIONS.map((minutes) => (
        <SettingsRow
          key={minutes}
          label={minutes === 0 ? "Never" : `${minutes} minutes`}
          value={data.screenOffMinutes === minutes ? "Current" : undefined}
          onSelect={async () => {
            await api.displayScreenOff(minutes).catch(() => undefined);
            refresh();
          }}
        />
      ))}
      {pending && <RevertConfirm onDone={finish} />}
    </div>
  );
}
