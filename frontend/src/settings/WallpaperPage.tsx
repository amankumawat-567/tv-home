import { useState } from "preact/hooks";
import { api } from "../api";
import { refreshState } from "../state/data";
import { SettingsRow } from "../components/SettingsRow";

export function WallpaperPage() {
  const [slideshow, setSlideshow] = useState(false);

  return (
    <div className="settings-page">
      <h1 className="settings-title">Wallpaper</h1>
      <div className="wallpaper-preview" style={{ backgroundImage: "url(/wallpaper)" }} />
      <SettingsRow
        label="Next wallpaper"
        onSelect={async () => {
          await api.wallpaperNext().catch(() => undefined);
          await refreshState();
        }}
      />
      <SettingsRow label="Slideshow" value={slideshow ? "On" : "Off"} onSelect={() => setSlideshow((s) => !s)} />
    </div>
  );
}
