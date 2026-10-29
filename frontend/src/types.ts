// Shared shapes for the TV Home API. Keep this in sync with backend/tv_home/models.py —
// it is the one contract the frontend and backend tracks build against independently.

export interface AppTile {
  id: string;
  name: string;
  domain: string;
  icon: boolean; // true once an icon has been fetched to /icons/{id}.png
}

export interface CatalogEntry {
  id: string;
  name: string;
  cat: string;
  domain: string;
  installed: boolean;
}

export interface WifiNetwork {
  ssid: string;
  signal: number; // 0-100
  secure: boolean;
  active: boolean;
  saved: boolean;
}

export interface WifiState {
  available: boolean;
  error?: string;
  wifiOn?: boolean;
  ethernet?: boolean;
  ip?: string;
  networks?: WifiNetwork[];
}

export interface BluetoothDevice {
  mac: string;
  name: string;
  paired: boolean;
  connected: boolean;
  kind?: "audio" | "input" | "phone" | "other";
}

export interface BluetoothState {
  available: boolean;
  error?: string;
  powered?: boolean;
  scanning?: boolean;
  devices?: BluetoothDevice[];
}

export interface SoundOutput {
  id: string;
  name: string;
  current: boolean;
}

export interface SoundState {
  available: boolean;
  error?: string;
  volume: number; // 0-100
  muted: boolean;
  outputs: SoundOutput[];
}

export interface DisplayMode {
  id: string;
  label: string; // e.g. "1920x1080 @ 60Hz"
  current: boolean;
}

export interface DisplayState {
  available: boolean;
  error?: string;
  modes: DisplayMode[];
  screenOffMinutes: number;
}

export interface DateTimeState {
  ntpSynced: boolean;
  timezone: string;
  clockWrong: boolean;
}

export interface SlideshowSettings {
  enabled: boolean;
  minutes: number;
}

export interface AboutInfo {
  system: string;
  processor: string;
  memory: string;
  storage: string;
  ip: string;
  version: string;
}

export interface UpdateInfo {
  current: string;
  latest: string;
  available: boolean;
  url: string | null;
  notes: string;
}

export interface StatusSnapshot {
  wifi: "off" | "none" | 0 | 1 | 2 | 3 | 4;
  bluetooth: "off" | "on" | "connected";
  volume: number;
  muted: boolean;
  clockWrong: boolean;
}

export interface AppState {
  user: string;
  wallpaper: boolean;
  apps: AppTile[];
  catalog: CatalogEntry[];
  status: StatusSnapshot;
}

export type RunningApp = { id: string; name: string } | null;

export interface ToastEvent {
  id: string;
  message: string;
  tone: "info" | "good" | "warn" | "bad";
}

// Pushed over WS /api/events. "state" carries a full AppState refresh (apps changed,
// status changed); "toast" asks the UI to show a short message; "running" tracks the
// one app that currently owns the foreground kiosk window.
export type ServerEvent =
  | { type: "state"; data: AppState }
  | { type: "toast"; data: ToastEvent }
  | { type: "running"; data: RunningApp };
