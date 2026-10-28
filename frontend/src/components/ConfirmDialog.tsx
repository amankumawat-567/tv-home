import { useFocusable } from "../focus/useFocusable";
import { closeConfirm, confirmRequest } from "../state/ui";

function DialogButton({ label, onSelect, autoFocus, danger }: { label: string; onSelect: () => void; autoFocus?: boolean; danger?: boolean }) {
  const { ref, focused } = useFocusable({ scope: "confirm", wrapGroup: "confirm-buttons", onSelect, autoFocus });
  return (
    <button
      ref={ref as never}
      className={`dialog-button focusable${focused ? " is-focused" : ""}${danger ? " is-danger" : ""}`}
      onClick={onSelect}
    >
      {label}
    </button>
  );
}

export function ConfirmDialog() {
  const req = confirmRequest.value;
  if (!req) return null;
  return (
    <div className="dialog-backdrop">
      <div className="dialog">
        <h2 className="dialog-title">{req.title}</h2>
        <p className="dialog-message">{req.message}</p>
        <div className="dialog-buttons">
          <DialogButton label="Cancel" onSelect={closeConfirm} autoFocus={req.tone === "danger"} />
          <DialogButton
            label={req.confirmLabel}
            danger={req.tone === "danger"}
            autoFocus={req.tone !== "danger"}
            onSelect={() => {
              const run = req.onConfirm;
              closeConfirm();
              run();
            }}
          />
        </div>
      </div>
    </div>
  );
}
