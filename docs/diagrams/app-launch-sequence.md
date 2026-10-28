# App launch / close sequence

What happens when you press Enter on a banner, and when you press Home to
close it — the PRD's A2/A3 requirements (`backend/tv_home/chrome.py`,
`frontend/src/state/nav.ts`).

```mermaid
sequenceDiagram
    actor U as You (remote/keyboard)
    participant UI as Frontend
    participant BE as Backend
    participant C as Chrome kiosk (app)

    U->>UI: Enter on a focused app banner
    UI->>UI: show Launch screen (logo) immediately
    UI->>BE: POST /api/apps/{id}/launch
    BE->>BE: find_chrome() on PATH
    alt Chrome found
        BE->>C: spawn --kiosk <app url>
        BE-->>UI: {ok: true}
        BE-->>UI: WS "running" event
        Note over UI: Launch screen clears when the<br/>window appears (or after 15s, A3)
    else Chrome missing / app unknown
        BE-->>UI: {ok: false, message}
        UI->>UI: clear Launch screen, show toast
    end

    U->>UI: Home key
    Note over UI: Home is grabbed globally by xbindkeys<br/>on the real PC, so it reaches the<br/>backend even while C has OS focus
    UI->>BE: POST /api/home
    BE->>BE: scan /proc for kiosk Chrome PIDs<br/>(matches by /proc/pid/exe, not argv —<br/>Chrome rewrites its own process title)
    BE->>C: SIGTERM
    BE-->>UI: {ok: true}
    UI->>UI: show Home within 1s (A2)
```
