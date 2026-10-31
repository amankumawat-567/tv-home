import { Fragment } from "preact";
import { useState } from "preact/hooks";
import { api } from "../api";
import { pushToast } from "../state/data";
import { askConfirm } from "../state/ui";
import { usePolling } from "../utils/usePolling";
import { SettingsRow } from "../components/SettingsRow";
import type { KdeConnectDevice } from "../types";

const ACTION_FN = {
  pair: "kdeconnectPair",
  accept: "kdeconnectAccept",
  reject: "kdeconnectReject",
  unpair: "kdeconnectUnpair",
  "install-remote": "kdeconnectInstallRemote",
} as const;

export function KdeConnectPage() {
  const { data, refresh } = usePolling(() => api.kdeconnect(), 5000);
  const [acting, setActing] = useState<string | null>(null);
  const [scanning, setScanning] = useState(false);

  if (!data) return <p className="settings-empty">Loading…</p>;
  if (!data.available) {
    return <p className="settings-empty">{data.error ?? "KDE Connect isn't installed or running."}</p>;
  }

  const run = async (device: KdeConnectDevice, action: keyof typeof ACTION_FN) => {
    setActing(device.id);
    const result = await api[ACTION_FN[action]](device.id, device.name).catch((e: Error) => ({ ok: false, message: e.message }));
    setActing(null);
    pushToast(result.message, result.ok ? "good" : "bad");
    refresh();
  };

  const devices = data.devices ?? [];
  // Re-pairing the same phone (e.g. after reinstalling its KDE Connect app)
  // creates a brand new device ID each time, leaving an old, no-longer-
  // reachable entry behind with the exact same name as the live one --
  // identical-looking rows made it easy to act on the wrong one (confirmed
  // the hard way: TV_REMOTE_COMMANDS got pushed to a stale duplicate while
  // the phone was actually talking to a different ID). Disambiguate by
  // showing a short ID suffix whenever a name isn't unique.
  const nameCounts = new Map<string, number>();
  for (const d of devices) nameCounts.set(d.name, (nameCounts.get(d.name) ?? 0) + 1);
  const labelFor = (d: KdeConnectDevice) => ((nameCounts.get(d.name) ?? 0) > 1 ? `${d.name} (${d.id.slice(0, 6)})` : d.name);

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
            label={labelFor(d)}
            value={
              acting === d.id
                ? "Working…"
                : d.incomingRequest
                  ? "Wants to pair"
                  : d.paired
                    ? d.reachable
                      ? "Paired"
                      : "Paired — not nearby"
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
              label={<span className="settings-row-indent">Reject {labelFor(d)}</span>}
              danger
              onSelect={() => void run(d, "reject")}
            />
          )}
          {d.paired && !d.incomingRequest && (
            <>
              <SettingsRow
                label={<span className="settings-row-indent">Set up TV remote for {labelFor(d)}</span>}
                disabled={!d.reachable}
                onSelect={() => void run(d, "install-remote")}
              />
              <SettingsRow
                label={<span className="settings-row-indent">Unpair {labelFor(d)}</span>}
                danger
                onSelect={() =>
                  askConfirm({
                    title: `Unpair ${labelFor(d)}?`,
                    message: "You'll need to pair it again to use it as a remote.",
                    confirmLabel: "Unpair",
                    tone: "danger",
                    onConfirm: () => void run(d, "unpair"),
                  })
                }
              />
            </>
          )}
        </Fragment>
      ))}
      {devices.length === 0 && <p className="settings-empty">No phones found yet. Open KDE Connect on your phone and try scanning.</p>}
    </div>
  );
}
