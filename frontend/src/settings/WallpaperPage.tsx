import { api } from "../api";
import { refreshState } from "../state/data";
import { usePolling } from "../utils/usePolling";
import { useFocusable } from "../focus/useFocusable";
import { SettingsRow } from "../components/SettingsRow";
import { CheckIcon } from "../components/Icons";
import type { WallpaperListItem } from "../types";

const INTERVALS = [5, 15, 30, 60];

function WallpaperTile({ item, current, onSelect }: { item: WallpaperListItem; current: boolean; onSelect: () => void }) {
  const { ref, focused } = useFocusable({ onSelect });
  return (
    <button
      ref={ref as never}
      className={`wallpaper-tile focusable${focused ? " is-focused" : ""}${current ? " is-current" : ""}`}
      style={{ backgroundImage: `url(/wallpaper/${item.index})` }}
      onClick={onSelect}
    >
      {current && <CheckIcon className="wallpaper-tile-check" size={18} />}
      <span className="wallpaper-tile-name">{item.name}</span>
    </button>
  );
}

export function WallpaperPage() {
  const { data: slideshow, refresh: refreshSlideshow } = usePolling(() => api.wallpaperSlideshow(), 10000);
  const { data: list, refresh: refreshList } = usePolling(() => api.wallpaperList(), 10000);

  const selectWallpaper = async (index: number) => {
    await api.wallpaperSet(index).catch(() => undefined);
    await Promise.all([refreshList(), refreshState()]);
  };

  return (
    <div className="settings-page">
      <h1 className="settings-title">Wallpaper</h1>

      {list && list.items.length > 0 ? (
        <div className="wallpaper-grid">
          {list.items.map((item) => (
            <WallpaperTile key={item.index} item={item} current={item.index === list.current} onSelect={() => void selectWallpaper(item.index)} />
          ))}
        </div>
      ) : (
        <p className="settings-empty">No wallpapers found.</p>
      )}

      <SettingsRow
        label="Slideshow"
        value={slideshow ? (slideshow.enabled ? "On" : "Off") : "…"}
        onSelect={async () => {
          if (!slideshow) return;
          await api.setWallpaperSlideshow(!slideshow.enabled, slideshow.minutes).catch(() => undefined);
          await refreshSlideshow();
        }}
      />
      {slideshow?.enabled && (
        <>
          <h2 className="settings-subtitle">Change every</h2>
          {INTERVALS.map((minutes) => (
            <SettingsRow
              key={minutes}
              label={`${minutes} minutes`}
              value={slideshow.minutes === minutes ? "Current" : undefined}
              onSelect={async () => {
                await api.setWallpaperSlideshow(true, minutes).catch(() => undefined);
                await refreshSlideshow();
              }}
            />
          ))}
        </>
      )}
    </div>
  );
}
