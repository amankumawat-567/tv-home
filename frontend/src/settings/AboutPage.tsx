import { api } from "../api";
import { usePolling } from "../utils/usePolling";
import { SettingsRow } from "../components/SettingsRow";

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
    </div>
  );
}
