import { api } from "../api";
import { refreshState } from "../state/data";
import { usePolling } from "../utils/usePolling";
import { SettingsRow } from "../components/SettingsRow";

const INTERVALS = [5, 15, 30, 60];

export function WallpaperPage() {
  const { data, refresh } = usePolling(() => api.wallpaperSlideshow(), 10000);

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
      <SettingsRow
        label="Slideshow"
        value={data ? (data.enabled ? "On" : "Off") : "…"}
        onSelect={async () => {
          if (!data) return;
          await api.setWallpaperSlideshow(!data.enabled, data.minutes).catch(() => undefined);
          await refresh();
        }}
      />
      {data?.enabled && (
        <>
          <h2 className="settings-subtitle">Change every</h2>
          {INTERVALS.map((minutes) => (
            <SettingsRow
              key={minutes}
              label={`${minutes} minutes`}
              value={data.minutes === minutes ? "Current" : undefined}
              onSelect={async () => {
                await api.setWallpaperSlideshow(true, minutes).catch(() => undefined);
                await refresh();
              }}
            />
          ))}
        </>
      )}
    </div>
  );
}
