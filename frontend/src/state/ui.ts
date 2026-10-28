import { signal } from "@preact/signals";
import { popScope, pushScope } from "../focus/engine";

export type HomeTab = "home" | "apps";
export type SettingsPage = "wifi" | "bluetooth" | "sound" | "display" | "datetime" | "wallpaper" | "about" | "power" | null;

export const activeTab = signal<HomeTab>("home");
export const quickSettingsOpen = signal(false);
export const settingsPage = signal<SettingsPage>(null);
export const appStoreOpen = signal(false);
export const quickSettingsInitialTile = signal<SettingsPage>(null);

export interface LaunchingState {
  id: string;
  name: string;
  startedAt: number;
}
export const launching = signal<LaunchingState | null>(null);

export interface ConfirmRequest {
  title: string;
  message: string;
  confirmLabel: string;
  tone?: "default" | "danger";
  onConfirm: () => void;
}
export const confirmRequest = signal<ConfirmRequest | null>(null);

export const screensaverActive = signal(false);

// The confirm dialog owns its own focus scope so Back closes just the dialog
// (cancelling) and returns focus to whatever asked for confirmation.
export function askConfirm(req: ConfirmRequest) {
  confirmRequest.value = req;
  pushScope("confirm");
}

export function closeConfirm() {
  if (!confirmRequest.value) return;
  confirmRequest.value = null;
  popScope();
}

export function closeAllOverlays() {
  quickSettingsOpen.value = false;
  settingsPage.value = null;
  appStoreOpen.value = false;
  if (confirmRequest.value) closeConfirm();
}
