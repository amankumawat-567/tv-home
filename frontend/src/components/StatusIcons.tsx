import type { ComponentChildren } from "preact";
import { useFocusable } from "../focus/useFocusable";
import { openQuickSettings } from "../state/nav";
import type { StatusSnapshot } from "../types";
import { BluetoothIcon, VolumeIcon, WifiIcon } from "./Icons";

function StatusButton({
  children,
  onSelect,
  label,
}: {
  children: ComponentChildren;
  onSelect: () => void;
  label: string;
}) {
  const { ref, focused } = useFocusable({ onSelect, wrapGroup: "topbar-status" });
  return (
    <button
      ref={ref as never}
      aria-label={label}
      className={`status-icon focusable${focused ? " is-focused" : ""}`}
      onClick={onSelect}
    >
      {children}
    </button>
  );
}

export function StatusIcons({ status }: { status: StatusSnapshot }) {
  const wifiLevel = status.wifi === "off" || status.wifi === "none" ? "off" : status.wifi;
  const btState = status.bluetooth;
  return (
    <div className="status-icons">
      <StatusButton label="Wi-Fi settings" onSelect={() => openQuickSettings("wifi")}>
        <WifiIcon level={wifiLevel as number | "off"} size={28} />
      </StatusButton>
      <StatusButton label="Bluetooth settings" onSelect={() => openQuickSettings("bluetooth")}>
        <BluetoothIcon state={btState} size={28} />
      </StatusButton>
      <StatusButton label="Sound settings" onSelect={() => openQuickSettings("sound")}>
        <VolumeIcon level={status.volume} muted={status.muted} size={28} />
      </StatusButton>
      {status.clockWrong && (
        <span className="status-warn" title="Clock needs syncing">
          !
        </span>
      )}
    </div>
  );
}
