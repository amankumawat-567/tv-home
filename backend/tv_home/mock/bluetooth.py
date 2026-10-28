"""Fake Bluetooth backend used when TV_HOME_MOCK=1 — mirrors system/bluetooth.py
(dbus-fast + BlueZ)'s shape. Defaults to "no adapter" since this PC has none yet
(see the PRD's constraints), toggled on here so the empty-state and the normal
flow can both be exercised without real hardware.
"""
import asyncio

_state = {
    "hasAdapter": True,  # flip to False to test the "no adapter" empty state
    "powered": True,
    "devices": [
        {"mac": "AA:BB:CC:00:11:22", "name": "Living Room Speaker", "paired": True, "connected": True},
        {"mac": "AA:BB:CC:00:11:33", "name": "Kitchen Earbuds", "paired": True, "connected": False},
        {"mac": "AA:BB:CC:00:11:44", "name": "Unknown Remote", "paired": False, "connected": False},
    ],
}


async def get_state(scan: bool = False) -> dict:
    if not _state["hasAdapter"]:
        return {
            "available": False,
            "error": "This PC has no Bluetooth adapter. Plug in a USB Bluetooth adapter to use Bluetooth.",
        }
    if scan:
        await asyncio.sleep(0.6)
    devices = sorted(_state["devices"], key=lambda d: (not d["connected"], not d["paired"], d["name"].lower()))
    return {"available": True, "powered": _state["powered"], "devices": devices}


async def set_power(on: bool) -> tuple[bool, str]:
    _state["powered"] = on
    return True, ""


def _find(mac: str) -> dict | None:
    return next((d for d in _state["devices"] if d["mac"] == mac), None)


async def connect(mac: str, name: str) -> tuple[bool, str]:
    d = _find(mac)
    if not d:
        return False, "Unknown device."
    await asyncio.sleep(0.5)
    d["paired"] = True
    d["connected"] = True
    return True, f"{name} connected."


async def disconnect(mac: str, name: str) -> tuple[bool, str]:
    d = _find(mac)
    if d:
        d["connected"] = False
    return True, f"{name} disconnected."


async def forget(mac: str, name: str) -> tuple[bool, str]:
    _state["devices"] = [d for d in _state["devices"] if d["mac"] != mac]
    return True, f"Forgot {name}."
