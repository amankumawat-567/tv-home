import { useFocusable } from "../focus/useFocusable";
import { selectSettingsCategory } from "../state/nav";
import { settingsPage, type SettingsPage } from "../state/ui";
import { WifiPage } from "../settings/WifiPage";
import { BluetoothPage } from "../settings/BluetoothPage";
import { SoundPage } from "../settings/SoundPage";
import { DisplayPage } from "../settings/DisplayPage";
import { DateTimePage } from "../settings/DateTimePage";
import { WallpaperPage } from "../settings/WallpaperPage";
import { AboutPage } from "../settings/AboutPage";
import { PowerPanel } from "../settings/PowerPanel";

const CATEGORIES: { id: Exclude<SettingsPage, null>; label: string }[] = [
  { id: "wifi", label: "Wi-Fi" },
  { id: "bluetooth", label: "Bluetooth" },
  { id: "sound", label: "Sound" },
  { id: "display", label: "Display" },
  { id: "datetime", label: "Date and time" },
  { id: "wallpaper", label: "Wallpaper" },
  { id: "about", label: "About" },
  { id: "power", label: "Power" },
];

function CategoryItem({ id, label }: { id: Exclude<SettingsPage, null>; label: string }) {
  const { ref, focused } = useFocusable({ scope: "settingsShell", onSelect: () => selectSettingsCategory(id) });
  const active = settingsPage.value === id;
  return (
    <button
      ref={ref as never}
      className={`settings-category focusable${focused ? " is-focused" : ""}${active ? " is-active" : ""}`}
      onClick={() => selectSettingsCategory(id)}
    >
      {label}
    </button>
  );
}

export function SettingsShell() {
  const page = settingsPage.value;
  return (
    <div className="settings-shell">
      <nav className="settings-list">
        {CATEGORIES.map((c) => (
          <CategoryItem key={c.id} id={c.id} label={c.label} />
        ))}
      </nav>
      <div className="settings-detail">
        {page === "wifi" && <WifiPage />}
        {page === "bluetooth" && <BluetoothPage />}
        {page === "sound" && <SoundPage />}
        {page === "display" && <DisplayPage />}
        {page === "datetime" && <DateTimePage />}
        {page === "wallpaper" && <WallpaperPage />}
        {page === "about" && <AboutPage />}
        {page === "power" && <PowerPanel />}
      </div>
    </div>
  );
}
