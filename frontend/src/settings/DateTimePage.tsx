import { api } from "../api";
import { usePolling } from "../utils/usePolling";
import { SettingsRow } from "../components/SettingsRow";
import { Clock, longDate } from "../components/Clock";

export function DateTimePage() {
  const { data } = usePolling(() => api.datetime(), 10000);

  return (
    <div className="settings-page">
      <h1 className="settings-title">Date and time</h1>
      <div className="settings-clock-preview">
        <Clock />
        <span className="settings-clock-date">{longDate()}</span>
      </div>
      {!data ? (
        <p className="settings-empty">Loading…</p>
      ) : (
        <>
          {data.clockWrong && <p className="settings-warning">The clock looks wrong — check your network connection so it can sync.</p>}
          <SettingsRow label="Network time (NTP)" value={data.ntpSynced ? "Synced" : "Not synced"} />
          <SettingsRow label="Time zone" value={data.timezone} />
        </>
      )}
    </div>
  );
}
