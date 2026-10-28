import { useFocusable } from "../focus/useFocusable";
import { activeTab } from "../state/ui";
import { openQuickSettings } from "../state/nav";
import type { StatusSnapshot } from "../types";
import { Clock } from "./Clock";
import { GearIcon } from "./Icons";
import { StatusIcons } from "./StatusIcons";

function Tab({ label, id }: { label: string; id: "home" | "apps" }) {
  const { ref, focused } = useFocusable({
    wrapGroup: "topbar-tabs",
    onSelect: () => (activeTab.value = id),
    // Home is the screen's default landing focus — explicit, so it wins
    // regardless of which sibling's useFocusable effect happens to fire first
    // (effects queue in the order each component's hooks are called during
    // render, which is not the same as visual/DOM order across components).
    autoFocus: id === "home",
  });
  const active = activeTab.value === id;
  return (
    <button
      ref={ref as never}
      className={`top-tab focusable${focused ? " is-focused" : ""}${active ? " is-active" : ""}`}
      onClick={() => (activeTab.value = id)}
    >
      {label}
    </button>
  );
}

function SettingsGearButton() {
  const { ref, focused } = useFocusable({ wrapGroup: "topbar-status", onSelect: () => openQuickSettings() });
  return (
    <button
      ref={ref as never}
      aria-label="Settings"
      className={`status-icon focusable${focused ? " is-focused" : ""}`}
      onClick={() => openQuickSettings()}
    >
      <GearIcon size={26} />
    </button>
  );
}

export function TopBar({ status }: { status: StatusSnapshot }) {
  return (
    <header className="top-bar">
      <nav className="top-tabs">
        <Tab label="Home" id="home" />
        <Tab label="Apps" id="apps" />
      </nav>
      <div className="top-status">
        <StatusIcons status={status} />
        <Clock className="top-clock" />
        <SettingsGearButton />
      </div>
    </header>
  );
}
