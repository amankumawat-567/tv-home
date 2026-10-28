# TV Home backend

FastAPI service that owns apps, Wi-Fi, Bluetooth, sound, display and power, and
pushes live state to the frontend over a WebSocket (`/api/events`).

## Development (mock mode — runs anywhere, no Linux/D-Bus/X11 needed)

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
TV_HOME_MOCK=1 uvicorn tv_home.main:app --reload --port 8000
```

Then `curl localhost:8000/api/state`, or run the frontend's `npm run dev`
alongside it (it proxies `/api`, `/icons`, `/wallpaper` here).

## Tests

```sh
pytest
```

Tests run against the mock providers (`tv_home/mock/*`) — they don't touch the
real system and pass on any OS.

## Real mode

Unset `TV_HOME_MOCK` (or set it to anything but `1`) to use the real
integrations in `tv_home/system/` — NetworkManager/BlueZ/logind over D-Bus,
`wpctl` for sound, `xrandr`/`xset` for display. These only work on the actual
Linux box with those services running; they were written to spec and are not
runnable on macOS, so they have not been exercised end-to-end. See the repo's
top-level README and the PRD's build plan for what to verify once installed on
the real PC.
