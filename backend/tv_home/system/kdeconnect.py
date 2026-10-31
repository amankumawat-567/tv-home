"""Real KDE Connect backend: dbus-fast talking to kdeconnectd over the SESSION
bus. This only handles pairing -- once a device is paired, KDE Connect's own
"Remote input" plugin on the phone injects mouse/keyboard events via XTest
straight into this X session, so TV Home itself never touches input routing,
only who's allowed to connect. See session/README.md.

The D-Bus surface here (service "org.kde.kdeconnect", daemon object at
/modules/kdeconnect, device objects at /modules/kdeconnect/devices/<id>, the
daemon's devices()/deviceNames() methods, and each device's
isPaired/isReachable/isPairRequestedByPeer properties and
requestPairing()/acceptPairing()/cancelPairing()/unpair() methods) is taken
directly from kdeconnect-kde's own source (core/daemon.h, core/device.h,
dbusinterfaces/dbusinterfaces.cpp), not guessed from CLI output.

NOT RUNNABLE on this macOS sandbox (no session D-Bus bus or kdeconnectd here)
-- verify once installed on the real PC. In particular: this assumes the
X session TV Home runs in has a working session D-Bus bus available (true
for a normal LightDM-launched xsession via the standard Xsession wrapper,
same as every other X11 convenience xbindkeys/xfwm4 already rely on) --
worth a first check on actual hardware.
"""
import asyncio

from dbus_fast.aio import MessageBus
from dbus_fast.constants import BusType

SERVICE = "org.kde.kdeconnect"
DAEMON_PATH = "/modules/kdeconnect"

_bus: MessageBus | None = None


async def _get_bus() -> MessageBus:
    global _bus
    if _bus is None:
        _bus = await MessageBus(bus_type=BusType.SESSION).connect()
    return _bus


async def _proxy(path: str):
    bus = await _get_bus()
    introspection = await bus.introspect(SERVICE, path)
    return bus.get_proxy_object(SERVICE, path, introspection)


async def _daemon():
    return (await _proxy(DAEMON_PATH)).get_interface("org.kde.kdeconnect.daemon")


async def _device(device_id: str):
    return (await _proxy(f"{DAEMON_PATH}/devices/{device_id}")).get_interface("org.kde.kdeconnect.device")


async def get_state(refresh: bool = False) -> dict:
    try:
        daemon = await _daemon()
    except Exception:
        return {"available": False, "error": "KDE Connect isn't installed or running."}

    if refresh:
        try:
            await daemon.call_force_on_network_change()
        except Exception:
            pass
        await asyncio.sleep(1.5)  # give the LAN broadcast a moment to find phones

    try:
        all_ids = await daemon.call_devices(False, False)
        names = await daemon.call_device_names(False, False)
    except Exception:
        return {"available": False, "error": "Couldn't talk to KDE Connect."}

    devices = []
    for dev_id in all_ids:
        try:
            iface = await _device(dev_id)
            paired = await iface.get_is_paired()
            reachable = await iface.get_is_reachable()
            incoming = await iface.get_is_pair_requested_by_peer()
        except Exception:
            continue
        devices.append(
            {
                "id": dev_id,
                "name": names.get(dev_id, dev_id),
                "paired": bool(paired),
                "reachable": bool(reachable),
                "incomingRequest": bool(incoming),
            }
        )
    devices.sort(key=lambda d: (not d["incomingRequest"], not d["paired"], not d["reachable"], d["name"].lower()))
    return {"available": True, "devices": devices}


async def pair(device_id: str, name: str) -> tuple[bool, str]:
    try:
        iface = await _device(device_id)
        await iface.call_request_pairing()
        return True, f"Pairing request sent to {name} — accept it on your phone."
    except Exception:
        return False, f"Couldn't reach {name}."


async def accept(device_id: str, name: str) -> tuple[bool, str]:
    try:
        iface = await _device(device_id)
        await iface.call_accept_pairing()
        return True, f"Paired with {name}."
    except Exception:
        return False, f"Couldn't accept pairing with {name}."


async def reject(device_id: str, name: str) -> tuple[bool, str]:
    try:
        iface = await _device(device_id)
        await iface.call_cancel_pairing()
        return True, f"Rejected {name}."
    except Exception:
        return False, f"Couldn't reject {name}."


async def unpair(device_id: str, name: str) -> tuple[bool, str]:
    try:
        iface = await _device(device_id)
        await iface.call_unpair()
        return True, f"Unpaired {name}."
    except Exception:
        return False, f"Couldn't unpair {name}."
