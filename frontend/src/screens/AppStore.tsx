import { useState } from "preact/hooks";
import { useFocusable } from "../focus/useFocusable";
import { api } from "../api";
import { appState, pushToast, refreshState } from "../state/data";
import { OnScreenKeyboard } from "../components/OnScreenKeyboard";
import type { CatalogEntry } from "../types";

function CatalogTile({ entry }: { entry: CatalogEntry }) {
  const [busy, setBusy] = useState(false);
  const toggle = async () => {
    setBusy(true);
    const result = entry.installed
      ? await api.remove(entry.id).catch((e: Error) => ({ ok: false, message: e.message }))
      : await api.install({ id: entry.id, name: entry.name, url: "" }).catch((e: Error) => ({ ok: false, message: e.message }));
    setBusy(false);
    if (!result.ok) pushToast(result.message, "bad");
    await refreshState();
  };
  const { ref, focused } = useFocusable({ onSelect: toggle, disabled: busy });
  return (
    <button ref={ref as never} className={`app-banner store-tile focusable${focused ? " is-focused" : ""}`} onClick={toggle}>
      <img
        className="app-banner-icon"
        src={`/icons/${entry.id}.png`}
        alt=""
        onError={(e) => ((e.target as HTMLImageElement).style.display = "none")}
      />
      <span className="store-tile-name">{entry.name}</span>
      <span className="store-tile-action">{busy ? "…" : entry.installed ? "Remove" : "Add"}</span>
    </button>
  );
}

function AddWebsiteTile({ onOpen }: { onOpen: () => void }) {
  const { ref, focused } = useFocusable({ onSelect: onOpen });
  return (
    <button ref={ref as never} className={`app-banner store-tile add-website-tile focusable${focused ? " is-focused" : ""}`} onClick={onOpen}>
      <span className="app-store-plus">+</span>
      <span className="store-tile-name">Add a website</span>
    </button>
  );
}

type AddStep = "closed" | "name" | "url";

export function AppStore() {
  const [step, setStep] = useState<AddStep>("closed");
  const [draftName, setDraftName] = useState("");
  const catalog = appState.value?.catalog ?? [];
  const categories = [...new Set(catalog.map((c) => c.cat))];

  const submitName = (name: string) => {
    if (!name.trim()) {
      setStep("closed");
      return;
    }
    setDraftName(name.trim());
    setStep("url");
  };

  const submitUrl = async (url: string) => {
    setStep("closed");
    const result = await api.install({ name: draftName, url }).catch((e: Error) => ({ ok: false, message: e.message }));
    pushToast(result.message, result.ok ? "good" : "bad");
    setDraftName("");
    await refreshState();
  };

  return (
    <div className="app-store">
      <h1 className="settings-title">App Store</h1>
      <div className="apps-grid">
        <AddWebsiteTile onOpen={() => setStep("name")} />
      </div>
      {categories.map((cat) => (
        <section className="store-category" key={cat}>
          <h2 className="row-title">{cat}</h2>
          <div className="apps-grid">
            {catalog
              .filter((c) => c.cat === cat)
              .map((entry) => (
                <CatalogTile key={entry.id} entry={entry} />
              ))}
          </div>
        </section>
      ))}
      {step === "name" && <OnScreenKeyboard label="App name" onSubmit={submitName} onCancel={() => setStep("closed")} />}
      {step === "url" && (
        <OnScreenKeyboard
          label={`Website for ${draftName}`}
          initialValue="https://"
          onSubmit={(v) => void submitUrl(v)}
          onCancel={() => setStep("closed")}
        />
      )}
    </div>
  );
}
