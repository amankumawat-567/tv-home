import { signal } from "@preact/signals";
import { popScope, pushScope } from "../focus/engine";

export type HomeTab = "home" | "apps";
export type SettingsPage =
  | "wifi"
  | "bluetooth"
  | "sound"
  | "display"
  | "datetime"
  | "wallpaper"
  | "about"
  | "power"
  | "remote"
  | "kdeconnect"
  | null;

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
  // Called when the dialog is dismissed WITHOUT confirming (Cancel button or
  // Back) — e.g. so a pending Bluetooth passkey confirmation can tell BlueZ
  // "rejected" instead of just leaving it hanging until it times out.
  onCancel?: () => void;
}
export const confirmRequest = signal<ConfirmRequest | null>(null);

export const screensaverActive = signal(false);

// The confirm dialog owns its own focus scope so Back closes just the dialog
// (cancelling) and returns focus to whatever asked for confirmation.
export function askConfirm(req: ConfirmRequest) {
  confirmRequest.value = req;
  pushScope("confirm");
}

// `confirmed` is true when this close follows the user pressing the confirm
// button — false for Cancel/Back, which fires `onCancel` instead.
export function closeConfirm(confirmed = false) {
  const req = confirmRequest.value;
  if (!req) return;
  confirmRequest.value = null;
  popScope();
  if (!confirmed) req.onCancel?.();
}

export function closeAllOverlays() {
  quickSettingsOpen.value = false;
  settingsPage.value = null;
  appStoreOpen.value = false;
  if (confirmRequest.value) closeConfirm();
}
