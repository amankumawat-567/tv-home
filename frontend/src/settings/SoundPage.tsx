import { api } from "../api";
import { usePolling } from "../utils/usePolling";
import { SettingsRow } from "../components/SettingsRow";

export function SoundPage() {
  const { data, refresh } = usePolling(() => api.sound(), 3000);

  if (!data) return <p className="settings-empty">Loading…</p>;
  if (!data.available) return <p className="settings-empty">{data.error ?? "Sound settings aren't available on this PC."}</p>;

  const bump = async (action: "up" | "down") => {
    await api.soundAction(action).catch(() => undefined);
    refresh();
  };

  return (
    <div className="settings-page">
      <h1 className="settings-title">Sound</h1>
      <SettingsRow label="Volume down" value={`${data.volume}%`} onSelect={() => bump("down")} />
      <SettingsRow label="Volume up" value={`${data.volume}%`} onSelect={() => bump("up")} />
      <SettingsRow
        label="Mute"
        value={data.muted ? "On" : "Off"}
        onSelect={async () => {
          await api.soundAction("mute").catch(() => undefined);
          refresh();
        }}
      />
      {data.outputs.length > 0 && (
        <>
          <h2 className="settings-subtitle">Output</h2>
          {data.outputs.map((o) => (
            <SettingsRow
              key={o.id}
              label={o.name}
              value={o.current ? "Current" : undefined}
              onSelect={async () => {
                await api.soundOutput(o.id).catch(() => undefined);
                refresh();
              }}
            />
          ))}
        </>
      )}
    </div>
  );
}
