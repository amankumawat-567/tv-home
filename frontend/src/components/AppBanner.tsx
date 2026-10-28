import { useEffect, useState } from "preact/hooks";
import { useFocusable } from "../focus/useFocusable";
import { onNav } from "../focus/navEvents";
import { popScope, pushScope } from "../focus/engine";
import { api } from "../api";
import { brandColorFor } from "../utils/brandColor";
import { launchApp } from "../state/nav";
import { askConfirm } from "../state/ui";
import { pushToast, refreshState } from "../state/data";
import type { AppTile } from "../types";

export function AppBanner({ app }: { app: AppTile }) {
  const [optionsOpen, setOptionsOpen] = useState(false);
  const [color, setColor] = useState("var(--surface-raised)");
  const { ref, focused } = useFocusable({
    onSelect: () => launchApp(app.id, app.name),
  });

  useEffect(() => {
    let cancelled = false;
    brandColorFor(app.id, app.icon ? `/icons/${app.id}.png` : null).then((c) => !cancelled && setColor(c));
    return () => {
      cancelled = true;
    };
  }, [app.id, app.icon]);

  // Hold OK on a focused tile opens a small options menu (move/remove), its own
  // focus scope so Back closes just the menu and returns focus to this tile.
  useEffect(() => {
    if (!focused) return;
    return onNav("holdSelect", () => {
      setOptionsOpen(true);
      pushScope(`tile-options:${app.id}`);
      return true;
    });
  }, [focused, app.id]);

  useEffect(() => {
    if (!optionsOpen) return;
    return onNav("back", () => {
      setOptionsOpen(false);
      popScope();
      return true;
    });
  }, [optionsOpen]);

  const closeOptions = () => {
    setOptionsOpen(false);
    popScope();
  };

  return (
    <div className="banner-wrap">
      <button
        ref={ref as never}
        className={`app-banner focusable${focused ? " is-focused" : ""}`}
        style={{ background: color }}
        onClick={() => launchApp(app.id, app.name)}
      >
        {app.icon ? (
          <img className="app-banner-icon" src={`/icons/${app.id}.png`} alt="" />
        ) : (
          <span className="app-banner-fallback">{app.name[0]}</span>
        )}
      </button>
      {focused && !optionsOpen && <div className="app-banner-name">{app.name}</div>}
      {optionsOpen && (
        <div className="tile-options">
          <OptionButton
            label="Move left"
            scope={`tile-options:${app.id}`}
            autoFocus
            onSelect={() => {
              void moveApp(app.id, "left");
              closeOptions();
            }}
          />
          <OptionButton
            label="Move right"
            scope={`tile-options:${app.id}`}
            onSelect={() => {
              void moveApp(app.id, "right");
              closeOptions();
            }}
          />
          <OptionButton
            label="Remove"
            scope={`tile-options:${app.id}`}
            onSelect={() => {
              closeOptions();
              askConfirm({
                title: "Remove app?",
                message: "This removes it from your home screen. You can always add it back from the App Store.",
                confirmLabel: "Remove",
                tone: "danger",
                onConfirm: () => void removeApp(app.id),
              });
            }}
          />
          <OptionButton label="Cancel" scope={`tile-options:${app.id}`} onSelect={closeOptions} />
        </div>
      )}
    </div>
  );
}

function OptionButton({
  label,
  onSelect,
  scope,
  autoFocus,
}: {
  label: string;
  onSelect: () => void;
  scope: string;
  autoFocus?: boolean;
}) {
  const { ref, focused } = useFocusable({ scope, wrapGroup: `${scope}-row`, onSelect, autoFocus });
  return (
    <button ref={ref as never} className={`tile-option focusable${focused ? " is-focused" : ""}`} onClick={onSelect}>
      {label}
    </button>
  );
}

async function moveApp(id: string, dir: "left" | "right") {
  await api.move(id, dir).catch(() => undefined);
  await refreshState();
}

async function removeApp(id: string) {
  const result = await api.remove(id).catch((e: Error) => ({ ok: false, message: e.message }) as const);
  if (!result.ok) pushToast(result.message || "Couldn't remove that app.", "bad");
  await refreshState();
}
