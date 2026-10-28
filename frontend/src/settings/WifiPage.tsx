import { useState } from "preact/hooks";
import { api } from "../api";
import { pushToast } from "../state/data";
import { askConfirm } from "../state/ui";
import { usePolling } from "../utils/usePolling";
import { SettingsRow } from "../components/SettingsRow";
import { OnScreenKeyboard } from "../components/OnScreenKeyboard";
import { LockIcon } from "../components/Icons";
import type { WifiNetwork } from "../types";

function SignalBars({ signal }: { signal: number }) {
  const bars = Math.max(1, Math.round(signal / 25));
  return <span className="signal-bars">{"▂▄▆█".slice(0, bars)}</span>;
}

export function WifiPage() {
  const { data, refresh } = usePolling(() => api.wifi(), 5000);
  const [connecting, setConnecting] = useState<WifiNetwork | null>(null);
  const [acting, setActing] = useState<string | null>(null);

  if (!data) return <p className="settings-empty">Loading…</p>;
  if (!data.available) return <p className="settings-empty">{data.error ?? "Wi-Fi isn't available on this PC."}</p>;

  const connect = async (net: WifiNetwork, password?: string) => {
    setConnecting(null);
    setActing(net.ssid);
    const result = await api.wifiConnect(net.ssid, password, net.saved).catch((e: Error) => ({ ok: false, message: e.message }));
    setActing(null);
    pushToast(result.message, result.ok ? "good" : "bad");
    refresh();
  };

  const forget = (net: WifiNetwork) =>
    askConfirm({
      title: `Forget ${net.ssid}?`,
      message: "You'll need to re-enter the password to connect to this network again.",
      confirmLabel: "Forget",
      tone: "danger",
      onConfirm: async () => {
        const result = await api.wifiForget(net.ssid).catch((e: Error) => ({ ok: false, message: e.message }));
        pushToast(result.message, result.ok ? "good" : "bad");
        refresh();
      },
    });

  return (
    <div className="settings-page">
      <h1 className="settings-title">Wi-Fi</h1>
      <SettingsRow
        label="Wi-Fi"
        value={data.wifiOn ? "On" : "Off"}
        onSelect={async () => {
          await api.wifiRadio(!data.wifiOn).catch(() => undefined);
          refresh();
        }}
      />
      {data.ip && <SettingsRow label="IP address" value={data.ip} />}
      {data.wifiOn &&
        (data.networks ?? []).map((net) => (
          <SettingsRow
            key={net.ssid}
            label={
              <>
                {net.secure && <LockIcon size={16} className="inline-icon" />} {net.ssid}
              </>
            }
            value={
              acting === net.ssid ? (
                "Connecting…"
              ) : net.active ? (
                "Connected"
              ) : (
                <>
                  {net.saved && <span className="settings-row-badge">Saved</span>}
                  <SignalBars signal={net.signal} />
                </>
              )
            }
            onSelect={() => {
              if (acting) return;
              if (net.active) {
                forget(net);
              } else if (net.secure && !net.saved) {
                setConnecting(net);
              } else {
                void connect(net);
              }
            }}
          />
        ))}
      {data.wifiOn && (data.networks ?? []).length === 0 && <p className="settings-empty">No networks found nearby.</p>}

      {connecting && (
        <OnScreenKeyboard
          label={`Password for ${connecting.ssid}`}
          secure
          submitLabel="Connect"
          onSubmit={(password) => void connect(connecting, password)}
          onCancel={() => setConnecting(null)}
        />
      )}
    </div>
  );
}
