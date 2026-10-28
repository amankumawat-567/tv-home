import { useEffect } from "preact/hooks";
import { useKeyNav } from "./focus/useKeyNav";
import { installNavController } from "./state/nav";
import { bootstrapData, appState } from "./state/data";
import { activeTab, appStoreOpen, quickSettingsOpen, settingsPage } from "./state/ui";
import { useScreensaver, Screensaver } from "./components/Screensaver";
import { TopBar } from "./components/TopBar";
import { Home } from "./screens/Home";
import { AppsTab } from "./screens/AppsTab";
import { QuickSettings } from "./components/QuickSettings";
import { SettingsShell } from "./screens/SettingsShell";
import { AppStore } from "./screens/AppStore";
import { ConfirmDialog } from "./components/ConfirmDialog";
import { LaunchScreen } from "./components/LaunchScreen";
import { ToastStack } from "./components/Toast";
import { RunningAppPlaceholder } from "./components/RunningAppPlaceholder";

export function App() {
  useKeyNav();
  useScreensaver();

  useEffect(() => {
    const stopNav = installNavController();
    const stopData = bootstrapData();
    return () => {
      stopNav();
      stopData();
    };
  }, []);

  const state = appState.value;

  return (
    <div className="app-shell">
      {state && (
        <>
          <TopBar status={state.status} />
          <main className="app-main">
            {activeTab.value === "home" ? <Home state={state} /> : <AppsTab state={state} />}
          </main>
        </>
      )}

      <RunningAppPlaceholder />
      <LaunchScreen />

      {settingsPage.value !== null ? (
        <SettingsShell />
      ) : (
        quickSettingsOpen.value && state && <QuickSettings status={state.status} />
      )}

      {appStoreOpen.value && <AppStore />}

      <ConfirmDialog />
      <ToastStack />
      <Screensaver />
    </div>
  );
}
