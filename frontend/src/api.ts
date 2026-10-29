import type {
  AppState,
  BluetoothState,
  DateTimeState,
  DisplayState,
  AboutInfo,
  ServerEvent,
  SlideshowSettings,
  SoundState,
  UpdateInfo,
  WifiState,
} from "./types";

// In dev, Vite proxies /api and /icons to the backend (see vite.config.ts).
// In production the backend serves the built frontend itself, so relative
// paths work unchanged.
const BASE = "";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    throw new Error(`${init?.method ?? "GET"} ${path} failed: ${res.status}`);
  }
  return (await res.json()) as T;
}

const post = <T>(path: string, body?: unknown) =>
  req<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined });

export const api = {
  state: () => req<AppState>("/api/state"),

  launch: (id: string) => post<{ ok: boolean; message: string }>(`/api/apps/${id}/launch`),
  home: () => post<{ ok: boolean }>("/api/home"),
  install: (body: { id?: string; name: string; url: string; ua?: string }) =>
    post<{ ok: boolean; message: string } & AppState>("/api/apps", body),
  remove: (id: string) => req<{ ok: boolean; message: string } & AppState>(`/api/apps/${id}`, { method: "DELETE" }),
  move: (id: string, dir: "left" | "right") => post<{ ok: boolean } & AppState>(`/api/apps/${id}/move`, { dir }),

  wifi: (rescan = false) => req<WifiState>(`/api/wifi${rescan ? "?scan=1" : ""}`),
  wifiRadio: (on: boolean) => post<{ ok: boolean; message: string }>("/api/wifi/radio", { on }),
  wifiConnect: (ssid: string, password?: string, saved?: boolean) =>
    post<{ ok: boolean; message: string }>("/api/wifi/connect", { ssid, password, saved }),
  wifiForget: (ssid: string) => post<{ ok: boolean; message: string }>("/api/wifi/forget", { ssid }),

  bluetooth: (scan = false) => req<BluetoothState>(`/api/bluetooth${scan ? "?scan=1" : ""}`),
  btPower: (on: boolean) => post<{ ok: boolean; message: string }>("/api/bluetooth/power", { on }),
  btConnect: (mac: string, name: string) => post<{ ok: boolean; message: string }>("/api/bluetooth/connect", { mac, name }),
  btDisconnect: (mac: string, name: string) => post<{ ok: boolean; message: string }>("/api/bluetooth/disconnect", { mac, name }),
  btForget: (mac: string, name: string) => post<{ ok: boolean; message: string }>("/api/bluetooth/forget", { mac, name }),

  sound: () => req<SoundState>("/api/sound"),
  soundAction: (action: "up" | "down" | "mute", ) => post<{ ok: boolean }>("/api/sound", { action }),
  soundOutput: (id: string) => post<{ ok: boolean }>("/api/sound", { action: "output", id }),

  display: () => req<DisplayState>("/api/display"),
  displaySet: (id: string) => post<{ ok: boolean; token: string }>("/api/display", { id }),
  displayConfirm: (token: string) => post<{ ok: boolean }>("/api/display/confirm", { token }),
  displayScreenOff: (minutes: number) => post<{ ok: boolean }>("/api/display/screen-off", { minutes }),

  datetime: () => req<DateTimeState>("/api/datetime"),
  about: () => req<AboutInfo>("/api/about"),

  power: (action: "sleep" | "restart" | "poweroff" | "desktop") =>
    post<{ ok: boolean; message: string }>("/api/power", { action }),

  wallpaperNext: () => post<{ ok: boolean }>("/api/wallpaper"),
  wallpaperSlideshow: () => req<SlideshowSettings>("/api/wallpaper/slideshow"),
  setWallpaperSlideshow: (enabled: boolean, minutes?: number) =>
    post<SlideshowSettings>("/api/wallpaper/slideshow", { enabled, minutes }),

  completeFirstRun: () => post<{ ok: boolean }>("/api/first-run/complete"),

  checkUpdate: () => req<UpdateInfo>("/api/update"),
  applyUpdate: (url?: string | null) => post<{ ok: boolean; message: string }>("/api/update/apply", { url }),
};

export function connectEvents(onEvent: (e: ServerEvent) => void): () => void {
  let socket: WebSocket | null = null;
  let closed = false;
  let retryMs = 1000;

  const connect = () => {
    if (closed) return;
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${proto}//${location.host}/api/events`;
    socket = new WebSocket(url);
    socket.onmessage = (ev) => {
      try {
        onEvent(JSON.parse(ev.data) as ServerEvent);
      } catch {
        // ignore malformed frames
      }
    };
    socket.onopen = () => {
      retryMs = 1000;
    };
    socket.onclose = () => {
      if (closed) return;
      setTimeout(connect, retryMs);
      retryMs = Math.min(retryMs * 2, 15000);
    };
    socket.onerror = () => socket?.close();
  };
  connect();

  return () => {
    closed = true;
    socket?.close();
  };
}
