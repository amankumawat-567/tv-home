import { api } from "../api";
import { askConfirm } from "../state/ui";
import { SettingsRow } from "../components/SettingsRow";

function confirmPower(action: "sleep" | "restart" | "poweroff" | "desktop", title: string, message: string) {
  askConfirm({
    title,
    message,
    confirmLabel: title,
    tone: action === "poweroff" ? "danger" : "default",
    onConfirm: () => void api.power(action).catch(() => undefined),
  });
}

export function PowerPanel() {
  return (
    <div className="settings-page">
      <h1 className="settings-title">Power</h1>
      <SettingsRow label="Sleep" onSelect={() => confirmPower("sleep", "Sleep", "Puts the PC to sleep. Press any remote key to wake it.")} />
      <SettingsRow label="Restart" onSelect={() => confirmPower("restart", "Restart", "TV Home will restart the PC now.")} />
      <SettingsRow label="Shut down" danger onSelect={() => confirmPower("poweroff", "Shut down", "This turns the PC off completely.")} />
      <SettingsRow label="Go to desktop" onSelect={() => confirmPower("desktop", "Go to desktop", "Leaves the TV Home screen for the regular desktop.")} />
    </div>
  );
}
