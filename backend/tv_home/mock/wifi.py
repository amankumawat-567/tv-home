"""Fake Wi-Fi backend used when TV_HOME_MOCK=1 — lets the whole UI run on a
laptop with no NetworkManager. Mirrors the shape system/wifi.py (dbus-fast +
NetworkManager) returns, so the frontend never knows which one it's talking to.
"""
import asyncio

_state = {
    "wifiOn": True,
    "connected": "Home Network",
    "saved": {"Home Network", "Office"},
    "networks": [
        {"ssid": "Home Network", "signal": 88, "secure": True},
        {"ssid": "Office", "signal": 54, "secure": True},
        {"ssid": "Neighbour's Wifi", "signal": 22, "secure": True},
        {"ssid": "Cafe Guest", "signal": 70, "secure": False},
    ],
}


async def get_state(scan: bool = False) -> dict:
    if not _state["wifiOn"]:
        return {"available": True, "wifiOn": False, "ethernet": False, "ip": "", "networks": []}
    networks = [
        {
            "ssid": n["ssid"],
            "signal": n["signal"],
            "secure": n["secure"],
            "active": n["ssid"] == _state["connected"],
            "saved": n["ssid"] in _state["saved"],
        }
        for n in _state["networks"]
    ]
    networks.sort(key=lambda n: (not n["active"], not n["saved"], -n["signal"]))
    return {
        "available": True,
        "wifiOn": True,
        "ethernet": False,
        "ip": "192.168.1.42" if _state["connected"] else "",
        "networks": networks,
    }


async def set_radio(on: bool) -> tuple[bool, str]:
    _state["wifiOn"] = on
    if not on:
        _state["connected"] = None
    return True, ""


async def connect(ssid: str, password: str | None, saved: bool) -> tuple[bool, str]:
    net = next((n for n in _state["networks"] if n["ssid"] == ssid), None)
    if not net:
        return False, "That network is out of range."
    await asyncio.sleep(0.4)
    if net["secure"] and not saved and not password:
        return False, "Wrong or missing password."
    if net["secure"] and not saved and password == "wrong":
        return False, "Wrong or missing password."
    _state["connected"] = ssid
    _state["saved"].add(ssid)
    return True, f"Connected to {ssid}."


async def forget(ssid: str) -> tuple[bool, str]:
    _state["saved"].discard(ssid)
    if _state["connected"] == ssid:
        _state["connected"] = None
    return True, f"Forgot {ssid}."
