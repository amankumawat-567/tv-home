import { useFocusable } from "../focus/useFocusable";
import { openAppStore } from "../state/nav";
import type { AppState } from "../types";
import { AppBanner } from "../components/AppBanner";

function AppStoreTile() {
  const { ref, focused } = useFocusable({ onSelect: openAppStore });
  return (
    <button ref={ref as never} className={`app-banner app-store-tile focusable${focused ? " is-focused" : ""}`} onClick={openAppStore}>
      <span className="app-store-plus">+</span>
      <span className="app-store-label">App Store</span>
    </button>
  );
}

export function AppsTab({ state }: { state: AppState }) {
  return (
    <div className="apps-tab">
      <h2 className="row-title">Apps</h2>
      <div className="apps-grid">
        <AppStoreTile />
        {state.apps.map((app) => (
          <AppBanner key={app.id} app={app} />
        ))}
      </div>
    </div>
  );
}
