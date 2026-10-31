"""Fake Bluetooth backend used when TV_HOME_MOCK=1 — mirrors system/bluetooth.py
(dbus-fast + BlueZ)'s shape, including its pairing-agent handshake: connect()
blocks the same way on a pending PIN/passkey request, resolved the same way
via respond_pairing_request(), so the frontend's dialog code exercises the
real flow without needing actual BlueZ hardware. Defaults to "no adapter"
since this PC has none yet (see the PRD's constraints), toggled on here so
the empty-state and the normal flow can both be exercised without real
hardware.
"""
import asyncio

_state = {
    "hasAdapter": True,  # flip to False to test the "no adapter" empty state
    "powered": True,
    "devices": [
        {"mac": "AA:BB:CC:00:11:22", "name": "Living Room Speaker", "paired": True, "connected": True},
        {"mac": "AA:BB:CC:00:11:33", "name": "Kitchen Earbuds", "paired": True, "connected": False},
        {"mac": "AA:BB:CC:00:11:44", "name": "Unknown Remote", "paired": False, "connected": False},
        # These two require the pairing-agent handshake below, mirroring
        # system/bluetooth.py's real BlueZ Agent1 callbacks — _pin devices
        # expect a fixed code typed on our side; _confirm devices show a
        # passkey on both sides for the user to confirm matches.
        {"mac": "AA:BB:CC:00:11:55", "name": "Old Bluetooth Keyboard", "paired": False, "connected": False, "_pin": "0000"},
        {"mac": "AA:BB:CC:00:11:66", "name": "Car Stereo", "paired": False, "connected": False, "_confirm": 583921},
    ],
}

_pending: dict | None = None
_pending_event: asyncio.Event | None = None
_pending_response: dict | None = None


async def get_state(scan: bool = False) -> dict:
    if not _state["hasAdapter"]:
        return {
            "available": False,
            "error": "This PC has no Bluetooth adapter. Plug in a USB Bluetooth adapter to use Bluetooth.",
        }
    if scan:
        await asyncio.sleep(0.6)
    devices = sorted(_state["devices"], key=lambda d: (not d["connected"], not d["paired"], d["name"].lower()))
    # Strip the mock-only "_pin"/"_confirm" hints -- those simulate what only
    # the real pairing agent would know, not something the API should expose.
    public = [{k: v for k, v in d.items() if not k.startswith("_")} for d in devices]
    return {"available": True, "powered": _state["powered"], "devices": public}


async def set_power(on: bool) -> tuple[bool, str]:
    _state["powered"] = on
    return True, ""


def _find(mac: str) -> dict | None:
    return next((d for d in _state["devices"] if d["mac"] == mac), None)


async def connect(mac: str, name: str) -> tuple[bool, str]:
    global _pending, _pending_event, _pending_response
    d = _find(mac)
    if not d:
        return False, "Unknown device."
    await asyncio.sleep(0.3)
    if not d["paired"] and ("_pin" in d or "_confirm" in d):
        kind = "pin" if "_pin" in d else "confirm"
        _pending = {"mac": mac, "name": name, "kind": kind, "passkey": d.get("_confirm")}
        _pending_event = asyncio.Event()
        _pending_response = None
        try:
            await asyncio.wait_for(_pending_event.wait(), timeout=60)
        except asyncio.TimeoutError:
            _pending = None
            return False, f"Pairing with {name} timed out."
        resp = _pending_response
        _pending = None
        ok = bool(resp) and (resp.get("value") == d.get("_pin") if kind == "pin" else bool(resp.get("accept")))
        if not ok:
            return False, f"Couldn't pair with {name}."
    d["paired"] = True
    d["connected"] = True
    return True, f"{name} connected."


def pairing_request() -> dict | None:
    return _pending


async def respond_pairing_request(value: str | None = None, accept: bool | None = None) -> bool:
    global _pending_response
    if not _pending_event:
        return False
    _pending_response = {"value": value, "accept": accept}
    _pending_event.set()
    return True


async def disconnect(mac: str, name: str) -> tuple[bool, str]:
    d = _find(mac)
    if d:
        d["connected"] = False
    return True, f"{name} disconnected."


async def forget(mac: str, name: str) -> tuple[bool, str]:
    _state["devices"] = [d for d in _state["devices"] if d["mac"] != mac]
    return True, f"Forgot {name}."
