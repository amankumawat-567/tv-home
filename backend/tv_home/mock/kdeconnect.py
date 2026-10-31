"""Fake KDE Connect backend used when TV_HOME_MOCK=1 — mirrors
system/kdeconnect.py's shape: a reachable-but-unpaired phone to pair with
(box-initiated), and a second phone that has already sent an incoming
pairing request (phone-initiated) for the Accept/Reject path.
"""
import asyncio

_state = {
    "available": True,  # flip to False to test the "not installed" empty state
    "devices": [
        {"id": "dev-office-laptop", "name": "Office Laptop", "paired": True, "reachable": True, "incomingRequest": False},
        {"id": "dev-pixel", "name": "Aman's Pixel", "paired": False, "reachable": True, "incomingRequest": False},
        {"id": "dev-old-phone", "name": "Old Phone", "paired": False, "reachable": True, "incomingRequest": True},
    ],
}


def _find(device_id: str) -> dict | None:
    return next((d for d in _state["devices"] if d["id"] == device_id), None)


async def get_state(refresh: bool = False) -> dict:
    if not _state["available"]:
        return {"available": False, "error": "KDE Connect isn't installed or running."}
    if refresh:
        await asyncio.sleep(0.6)
    devices = sorted(
        _state["devices"],
        key=lambda d: (not d["incomingRequest"], not d["paired"], not d["reachable"], d["name"].lower()),
    )
    return {"available": True, "devices": devices}


async def pair(device_id: str, name: str) -> tuple[bool, str]:
    d = _find(device_id)
    if not d:
        return False, "Unknown device."
    await asyncio.sleep(0.3)
    d["paired"] = True
    return True, f"Paired with {name}."


async def accept(device_id: str, name: str) -> tuple[bool, str]:
    d = _find(device_id)
    if not d:
        return False, "Unknown device."
    d["paired"] = True
    d["incomingRequest"] = False
    return True, f"Paired with {name}."


async def reject(device_id: str, name: str) -> tuple[bool, str]:
    d = _find(device_id)
    if d:
        d["incomingRequest"] = False
    return True, f"Rejected {name}."


async def unpair(device_id: str, name: str) -> tuple[bool, str]:
    d = _find(device_id)
    if d:
        d["paired"] = False
    return True, f"Unpaired {name}."


async def install_remote(device_id: str, name: str) -> tuple[bool, str]:
    d = _find(device_id)
    if not d:
        return False, "Unknown device."
    return True, f"TV remote set up for {name} — check Run Commands in its KDE Connect app."
