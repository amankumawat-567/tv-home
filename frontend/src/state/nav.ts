// Central place that opens/closes every overlay (quick settings, a settings
// subpage, the App Store, a confirm dialog) in lockstep with the focus-engine's
// scope stack, so Back always unwinds exactly one of these and restores focus to
// whatever opened it — the PRD's own navigation rule.
import { popScope, pushScope } from "../focus/engine";
import { api } from "../api";
import { onNav } from "../focus/navEvents";
import { refreshState, runningApp, pushToast } from "./data";
import {
  activeTab,
  appStoreOpen,
  closeConfirm,
  confirmRequest,
  launching,
  quickSettingsInitialTile,
  quickSettingsOpen,
  settingsPage,
  type SettingsPage,
} from "./ui";

export function openQuickSettings(focusTile: SettingsPage = null) {
  quickSettingsInitialTile.value = focusTile;
  if (quickSettingsOpen.value) return;
  quickSettingsOpen.value = true;
  pushScope("quickSettings");
}

export function closeQuickSettings() {
  if (!quickSettingsOpen.value) return;
  quickSettingsOpen.value = false;
  settingsPage.value = null;
  popScope();
}

/** Enter the Settings shell (list-left/detail-right) focused on one category —
 * from a QuickSettings tile, or a status icon via openQuickSettings+here. */
export function openSettingsPage(page: Exclude<SettingsPage, null>) {
  settingsPage.value = page;
  pushScope("settingsShell");
}

/** Switch categories *within* an already-open Settings shell — lateral, not a
 * new nav depth, so it does not touch the focus-scope stack. */
export function selectSettingsCategory(page: Exclude<SettingsPage, null>) {
  settingsPage.value = page;
}

export function closeSettingsPage() {
  settingsPage.value = null;
  popScope();
}

export function openAppStore() {
  appStoreOpen.value = true;
  pushScope("appStore");
}

export function closeAppStore() {
  appStoreOpen.value = false;
  popScope();
}

async function goHome() {
  if (runningApp.value) {
    await api.home().catch(() => undefined);
    runningApp.value = null;
  }
  launching.value = null;
  // Unwind every overlay back to the root scope.
  while (confirmRequest.value || appStoreOpen.value || settingsPage.value || quickSettingsOpen.value) {
    if (confirmRequest.value) closeConfirm();
    else if (appStoreOpen.value) closeAppStore();
    else if (settingsPage.value) closeSettingsPage();
    else closeQuickSettings();
  }
  activeTab.value = "home";
}

/** Wires the semantic nav events (see focus/navEvents) to the overlay stack.
 * Call once, at the app root. */
export function installNavController() {
  const unsubs = [
    onNav("back", () => {
      if (confirmRequest.value) {
        closeConfirm();
        return true;
      }
      if (settingsPage.value) {
        closeSettingsPage();
        return true;
      }
      if (appStoreOpen.value) {
        closeAppStore();
        return true;
      }
      if (quickSettingsOpen.value) {
        closeQuickSettings();
        return true;
      }
      return false;
    }),
    onNav("home", () => {
      void goHome();
      return true;
    }),
    onNav("holdHome", () => {
      if (!quickSettingsOpen.value) openQuickSettings();
      return true;
    }),
    onNav("menu", () => {
      if (!quickSettingsOpen.value) openQuickSettings();
      return true;
    }),
    onNav("recoveryDesktop", () => {
      api.power("desktop").catch(() => undefined);
      return true;
    }),
  ];
  return () => unsubs.forEach((u) => u());
}

export async function launchApp(id: string, name: string) {
  launching.value = { id, name, startedAt: Date.now() };
  const result = await api.launch(id).catch((err: Error) => ({ ok: false, message: err.message }));
  if (!result.ok) {
    pushToast(result.message || `Couldn't open ${name}.`, "bad");
    launching.value = null;
    return;
  }
  runningApp.value = { id, name };
  // The launch screen clears once the app's window appears; the backend has no
  // direct signal for that over HTTP polling, so mirror the PRD's own 15s
  // timeout (A3) and otherwise let the "running" WS event (or a window losing
  // focus back to the kiosk home) end it. A short fixed delay keeps this
  // sandbox-testable without a real window manager.
  setTimeout(() => {
    if (launching.value?.id === id) launching.value = null;
  }, 15000);
  refreshState().catch(() => undefined);
}
