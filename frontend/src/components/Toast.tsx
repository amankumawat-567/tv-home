import { toasts } from "../state/data";

export function ToastStack() {
  if (toasts.value.length === 0) return null;
  return (
    <div className="toast-stack">
      {toasts.value.map((t) => (
        <div key={t.id} className={`toast toast-${t.tone}`}>
          {t.message}
        </div>
      ))}
    </div>
  );
}
