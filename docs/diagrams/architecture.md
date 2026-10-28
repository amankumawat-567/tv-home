# Architecture diagram

Companion to `docs/ARCHITECTURE.md` §2. The frontend only ever talks to the
backend's REST/WS API — it never knows whether `mock/` or `system/` is behind
it.

```mermaid
flowchart TB
    subgraph Client["Chrome kiosk window"]
        UI["Frontend\nPreact + TypeScript"]
        FE["Focus engine\n(arrow keys → DOM geometry)"]
        UI --- FE
    end

    subgraph Server["Backend — one local FastAPI process"]
        API["Routes\n/api/state, /api/apps, /api/wifi, ..."]
        APPS["apps.py / chrome.py\ninstall, launch, close"]
        PROV["providers.py\npicks mock vs. real per module"]
        API --> APPS
        API --> PROV
    end

    subgraph Mock["mock/ — TV_HOME_MOCK=1"]
        MWIFI[wifi.py]
        MBT[bluetooth.py]
        MSND[sound.py]
        MDISP[display.py]
        MPWR[power.py]
    end

    subgraph Real["system/ — real Linux only"]
        RWIFI["wifi.py\ndbus-fast → NetworkManager"]
        RBT["bluetooth.py\ndbus-fast → BlueZ"]
        RSND["sound.py\nwpctl"]
        RDISP["display.py\nxrandr / xset"]
        RPWR["power.py\ndbus-fast → logind"]
    end

    UI <-->|"REST + WebSocket\n/api/events"| API
    PROV -.->|TV_HOME_MOCK=1| Mock
    PROV -.->|real PC| Real

    APPS -->|spawns/kills| Chrome2["Chrome kiosk window\n(the launched app)"]

    classDef unverified fill:#3a2a1a,stroke:#f5c451,color:#f1f3f5;
    class Real unverified
```

Orange = written to spec but unverified in this dev environment (no D-Bus,
NetworkManager, BlueZ, PipeWire or X11 on macOS) — see each module's own
header comment and `docs/TODO.md`.
