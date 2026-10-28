# Boot and recovery flow

What happens from power-on to Home, and the paths back to the regular
desktop — `session/tv-home-session.sh`. **Unverified**: this only runs on the
real Xubuntu PC (LightDM, X11, systemd); see `session/README.md`.

```mermaid
flowchart TD
    Boot([Power on]) --> LightDM[LightDM autologin]
    LightDM --> Session["tv-home-session.sh starts:\nxfwm4 --compositor=off, xbindkeys"]
    Session --> CrashCheck{"3+ crashes in\nlast 5 minutes?"}
    CrashCheck -->|yes| Desktop
    CrashCheck -->|no| StartBackend["systemctl --user restart\ntv-home-backend.service"]
    StartBackend --> WaitBackend{"Backend answers\n/api/state within ~10s?"}
    WaitBackend -->|no| RecordCrash[record a crash] --> CrashCheck
    WaitBackend -->|yes| Chrome["Launch Chrome kiosk\nat http://127.0.0.1:8000/"]
    Chrome --> ChromeExit[Chrome window exits]
    ChromeExit --> SentinelCheck{"go-desktop\nsentinel file present?"}
    SentinelCheck -->|yes| Desktop
    SentinelCheck -->|no| RecordCrash

    Desktop(["exec startxfce4\n(regular desktop)"])

    CtrlAltD(["Ctrl+Alt+D\n(xbindkeys, any time)"]) -.->|"tv-home-recover.sh —\ndoesn't depend on the\nbackend being alive"| Desktop
    PowerPanel(["Settings → Power →\nGo to desktop"]) -.->|writes the sentinel,\nthen exits| ChromeExit
```

Three independent paths reach the desktop: the crash counter (Y2), the
sentinel file a normal "Go to desktop" action writes, and Ctrl+Alt+D's
recovery script, which is deliberately self-contained so it still works if
the backend has crashed outright (Y3).
