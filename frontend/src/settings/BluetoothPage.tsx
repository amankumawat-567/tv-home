import { Fragment } from "preact";
import { useState } from "preact/hooks";
import { api } from "../api";
import { pushToast } from "../state/data";
import { askConfirm } from "../state/ui";
import { usePolling } from "../utils/usePolling";
import { SettingsRow } from "../components/SettingsRow";
import type { BluetoothDevice } from "../types";

export function BluetoothPage() {
  const { data, refresh } = usePolling(() => api.bluetooth(), 5000);
  const [acting, setActing] = useState<string | null>(null);
  const [scanning, setScanning] = useState(false);

  if (!data) return <p className="settings-empty">Loading…</p>;
  if (!data.available) {
    return <p className="settings-empty">{data.error ?? "This PC has no Bluetooth adapter. Plug in a USB Bluetooth adapter to use Bluetooth."}</p>;
  }

  const run = async (device: BluetoothDevice, action: "connect" | "disconnect" | "forget") => {
    setActing(device.mac);
    const result = await api[action === "connect" ? "btConnect" : action === "disconnect" ? "btDisconnect" : "btForget"](
      device.mac,
      device.name,
    ).catch((e: Error) => ({ ok: false, message: e.message }));
    setActing(null);
    pushToast(result.message, result.ok ? "good" : "bad");
    refresh();
  };

  const select = (device: BluetoothDevice) => {
    if (acting) return;
    if (device.connected) {
      askConfirm({
        title: `Disconnect ${device.name}?`,
        message: "You can reconnect any time from this list.",
        confirmLabel: "Disconnect",
        onConfirm: () => void run(device, "disconnect"),
      });
    } else {
      void run(device, "connect");
    }
  };

  return (
    <div className="settings-page">
      <h1 className="settings-title">Bluetooth</h1>
      <SettingsRow
        label="Bluetooth"
        value={data.powered ? "On" : "Off"}
        onSelect={async () => {
          await api.btPower(!data.powered).catch(() => undefined);
          refresh();
        }}
      />
      {data.powered && (
        <SettingsRow
          label="Scan for devices"
          value={scanning ? "Scanning…" : undefined}
          onSelect={async () => {
            setScanning(true);
            await api.bluetooth(true).catch(() => undefined);
            setScanning(false);
            refresh();
          }}
        />
      )}
      {data.powered &&
        (data.devices ?? []).map((d) => (
          <Fragment key={d.mac}>
            <SettingsRow
              label={d.name || d.mac}
              value={acting === d.mac ? "Working…" : d.connected ? "Connected" : d.paired ? "Paired" : "Available"}
              onSelect={() => select(d)}
            />
            {d.paired && (
              <SettingsRow
                label={<span className="settings-row-indent">Forget {d.name || d.mac}</span>}
                danger
                onSelect={() =>
                  askConfirm({
                    title: `Forget ${d.name || d.mac}?`,
                    message: "You'll need to pair it again to use it with TV Home.",
                    confirmLabel: "Forget",
                    tone: "danger",
                    onConfirm: () => void run(d, "forget"),
                  })
                }
              />
            )}
          </Fragment>
        ))}
      {data.powered && (data.devices ?? []).length === 0 && <p className="settings-empty">No devices found yet. Try scanning.</p>}
    </div>
  );
}
