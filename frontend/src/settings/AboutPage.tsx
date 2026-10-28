import { useState } from "preact/hooks";
import { api } from "../api";
import { pushToast } from "../state/data";
import { usePolling } from "../utils/usePolling";
import { SettingsRow } from "../components/SettingsRow";

function UpdateRow() {
  const { data: update, refresh } = usePolling(() => api.checkUpdate(), 6 * 60 * 60 * 1000); // Y6: check periodically, not on every render
  const [applying, setApplying] = useState(false);

  if (!update) {
    return <SettingsRow label="Check for updates" value="Checking…" />;
  }
  if (!update.available) {
    return <SettingsRow label="Software update" value={`Up to date (${update.current})`} onSelect={() => void refresh()} />;
  }
  return (
    <SettingsRow
      label={`Update to ${update.latest}`}
      value={applying ? "Updating…" : "Install"}
      disabled={applying}
      onSelect={async () => {
        setApplying(true);
        const result = await api.applyUpdate(update.url).catch((e: Error) => ({ ok: false, message: e.message }));
        setApplying(false);
        pushToast(result.message, result.ok ? "good" : "bad");
        if (result.ok) void refresh();
      }}
    />
  );
}

export function AboutPage() {
  const { data } = usePolling(() => api.about(), 15000);
  if (!data) return <p className="settings-empty">Loading…</p>;
  return (
    <div className="settings-page">
      <h1 className="settings-title">About</h1>
      <SettingsRow label="System" value={data.system} />
      <SettingsRow label="Processor" value={data.processor} />
      <SettingsRow label="Memory" value={data.memory} />
      <SettingsRow label="Storage" value={data.storage} />
      <SettingsRow label="IP address" value={data.ip} />
      <SettingsRow label="TV Home version" value={data.version} />
      <UpdateRow />
    </div>
  );
}
