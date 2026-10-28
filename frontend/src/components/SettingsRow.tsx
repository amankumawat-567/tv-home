import type { ComponentChildren } from "preact";
import { useFocusable } from "../focus/useFocusable";

export function SettingsRow({
  label,
  value,
  onSelect,
  disabled,
  danger,
}: {
  label: ComponentChildren;
  value?: ComponentChildren;
  onSelect?: () => void;
  disabled?: boolean;
  danger?: boolean;
}) {
  const { ref, focused } = useFocusable({ onSelect: onSelect ?? (() => undefined), disabled: disabled || !onSelect });
  return (
    <button
      ref={ref as never}
      className={`settings-row focusable${focused ? " is-focused" : ""}${danger ? " is-danger" : ""}${disabled ? " is-disabled" : ""}`}
      onClick={onSelect}
      disabled={disabled}
    >
      <span className="settings-row-label">{label}</span>
      {value !== undefined && <span className="settings-row-value">{value}</span>}
    </button>
  );
}
