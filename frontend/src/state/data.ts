import { signal } from "@preact/signals";
import { api, connectEvents } from "../api";
import type { AppState, RunningApp, ToastEvent } from "../types";

export const appState = signal<AppState | null>(null);
export const runningApp = signal<RunningApp>(null);
export const toasts = signal<ToastEvent[]>([]);

let toastSeq = 0;
export function pushToast(message: string, tone: ToastEvent["tone"] = "info") {
  const toast: ToastEvent = { id: `t${++toastSeq}`, message, tone };
  toasts.value = [...toasts.value, toast];
  setTimeout(() => {
    toasts.value = toasts.value.filter((t) => t.id !== toast.id);
  }, 4000);
}

export async function refreshState() {
  appState.value = await api.state();
}

export function bootstrapData(): () => void {
  refreshState().catch(() => pushToast("Couldn't reach the TV Home service.", "bad"));

  return connectEvents((event) => {
    if (event.type === "state") appState.value = event.data;
    else if (event.type === "toast") pushToast(event.data.message, event.data.tone);
    else if (event.type === "running") runningApp.value = event.data;
  });
}
