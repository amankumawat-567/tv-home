import type { ComponentChildren } from "preact";
import { useEffect } from "preact/hooks";
import { useFocusable } from "../focus/useFocusable";
import { setFocus } from "../focus/engine";
import { openSettingsPage } from "../state/nav";
import { quickSettingsInitialTile, type SettingsPage } from "../state/ui";
import { BluetoothIcon, DisplayIcon, GearIcon, PowerIcon, VolumeIcon, WifiIcon } from "./Icons";
import { Clock, longDate } from "./Clock";
import type { StatusSnapshot } from "../types";

function Tile({ label, icon, page }: { label: string; icon: ComponentChildren; page: Exclude<SettingsPage, null> }) {
  const { ref, focused, id } = useFocusable({ scope: "quickSettings", onSelect: () => openSettingsPage(page) });
  useEffect(() => {
    if (quickSettingsInitialTile.value === page) setFocus(id);
  }, [id, page]);
  return (
    <button ref={ref as never} className={`quick-tile focusable${focused ? " is-focused" : ""}`} onClick={() => openSettingsPage(page)}>
      <span className="quick-tile-icon">{icon}</span>
      <span className="quick-tile-label">{label}</span>
    </button>
  );
}

export function QuickSettings({ status }: { status: StatusSnapshot }) {
  return (
    <aside className="quick-settings">
      <div className="quick-settings-datetime">
        <Clock className="quick-settings-clock" />
        <div className="quick-settings-date">{longDate()}</div>
      </div>
      <div className="quick-tiles">
        <Tile label="Wi-Fi" page="wifi" icon={<WifiIcon level={status.wifi === "off" || status.wifi === "none" ? "off" : status.wifi} size={32} />} />
        <Tile label="Bluetooth" page="bluetooth" icon={<BluetoothIcon state={status.bluetooth} size={32} />} />
        <Tile label="Sound" page="sound" icon={<VolumeIcon level={status.volume} muted={status.muted} size={32} />} />
        <Tile label="Display" page="display" icon={<DisplayIcon size={32} />} />
        <Tile label="Power" page="power" icon={<PowerIcon size={32} />} />
        <Tile label="Settings" page="wifi" icon={<GearIcon size={32} />} />
      </div>
    </aside>
  );
}
