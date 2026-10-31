import { Fragment } from "preact";
import { useState } from "preact/hooks";
import { api } from "../api";
import { pushToast } from "../state/data";
import { askConfirm } from "../state/ui";
import { usePolling } from "../utils/usePolling";
import { SettingsRow } from "../components/SettingsRow";
import type { KdeConnectDevice } from "../types";

export function KdeConnectPage() {
  const { data, refresh } = usePolling(() => api.kdeconnect(), 5000);
  const [acting, setActing] = useState<string | null>(null);
  const [scanning, setScanning] = useState(false);

  if (!data) return <p className="settings-empty">Loading…</p>;
  if (!data.available) {
    return <p className="settings-empty">{data.error ?? "KDE Connect isn't installed or running."}</p>;
  }

  const run = async (device: KdeConnectDevice, action: "pair" | "accept" | "reject" | "unpair") => {
    setActing(device.id);
    const fn = action === "pair" ? "kdeconnectPair" : action === "accept" ? "kdeconnectAccept" : action === "reject" ? "kdeconnectReject" : "kdeconnectUnpair";
    const result = await api[fn](device.id, device.name).catch((e: Error) => ({ ok: false, message: e.message }));
    setActing(null);
    pushToast(result.message, result.ok ? "good" : "bad");
    refresh();
  };

  const devices = data.devices ?? [];

  return (
    <div className="settings-page">
      <h1 className="settings-title">Remote connect (KDE Connect)</h1>
      <p className="dialog-message">
        Pair your phone to use its KDE Connect app as a trackpad and keyboard for TV Home — install the KDE Connect app on your phone first, then pick
        it below. Once paired, look for "Run Commands" in the KDE Connect app for a ready-made TV remote (D-pad, OK, Back, Home, Menu, volume) — set up
        automatically, no extra configuration needed.
      </p>
      <SettingsRow
        label="Scan for phones"
        value={scanning ? "Scanning…" : undefined}
        onSelect={async () => {
          setScanning(true);
          await api.kdeconnect(true).catch(() => undefined);
          setScanning(false);
          refresh();
        }}
      />
      {devices.map((d) => (
        <Fragment key={d.id}>
          <SettingsRow
            label={d.name}
            value={
              acting === d.id
                ? "Working…"
                : d.incomingRequest
                  ? "Wants to pair"
                  : d.paired
                    ? "Paired"
                    : d.reachable
                      ? "Available"
                      : "Not nearby"
            }
            onSelect={() => {
              if (acting || d.paired) return;
              if (d.incomingRequest) void run(d, "accept");
              else if (d.reachable) void run(d, "pair");
            }}
          />
          {d.incomingRequest && (
            <SettingsRow
              label={<span className="settings-row-indent">Reject {d.name}</span>}
              danger
              onSelect={() => void run(d, "reject")}
            />
          )}
          {d.paired && !d.incomingRequest && (
            <SettingsRow
              label={<span className="settings-row-indent">Unpair {d.name}</span>}
              danger
              onSelect={() =>
                askConfirm({
                  title: `Unpair ${d.name}?`,
                  message: "You'll need to pair it again to use it as a remote.",
                  confirmLabel: "Unpair",
                  tone: "danger",
                  onConfirm: () => void run(d, "unpair"),
                })
              }
            />
          )}
        </Fragment>
      ))}
      {devices.length === 0 && <p className="settings-empty">No phones found yet. Open KDE Connect on your phone and try scanning.</p>}
    </div>
  );
}
