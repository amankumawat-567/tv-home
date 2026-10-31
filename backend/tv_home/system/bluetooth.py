"""Real Bluetooth backend: dbus-fast talking to BlueZ, per the PRD's stack table.

NOT RUNNABLE OR TESTED on this macOS sandbox (no D-Bus system bus or bluetoothd
here, and this PC has no Bluetooth adapter yet either) — written to spec against
BlueZ's documented D-Bus API; verify once a USB Bluetooth adapter is attached.

Pairing agent: some devices (old peripherals needing a fixed PIN, or anything
using numeric-comparison pairing) need something to answer BlueZ's pairing
agent callbacks (RequestPinCode/RequestPasskey/RequestConfirmation) — without
one registered, those pairings just fail. _PairingAgent below bridges those
callbacks to the UI via a one-at-a-time pending-request slot: connect()
registers it once, a callback firing sets pending_pairing_request() and
awaits a response that the frontend supplies via respond_pairing_request()
(see routes/bluetooth.py's /pairing endpoints) — the same side-channel-poll
shape phone_type.py already uses for its own out-of-band handshake.
"""
import asyncio
from dataclasses import dataclass, field

from dbus_fast import DBusError
from dbus_fast.aio import MessageBus
from dbus_fast.constants import BusType
from dbus_fast.service import ServiceInterface, method

BLUEZ = "org.bluez"
AGENT_PATH = "/tv_home/agent"

_bus: MessageBus | None = None
_agent_registered = False


async def _get_bus() -> MessageBus:
    global _bus
    if _bus is None:
        _bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
    return _bus


async def _proxy(path: str):
    bus = await _get_bus()
    introspection = await bus.introspect(BLUEZ, path)
    return bus.get_proxy_object(BLUEZ, path, introspection)


async def _managed_objects() -> dict:
    root = (await _proxy("/")).get_interface("org.freedesktop.DBus.ObjectManager")
    return await root.call_get_managed_objects()


@dataclass
class _PendingRequest:
    mac: str
    name: str
    kind: str  # "pin" | "passkey" | "confirm" | "authorize" | "display"
    passkey: int | None = None
    event: asyncio.Event = field(default_factory=asyncio.Event)
    response: dict | None = None


_pending: _PendingRequest | None = None


async def _device_info(path: str) -> tuple[str, str]:
    for p, ifaces in (await _managed_objects()).items():
        if p == path:
            dev = ifaces.get("org.bluez.Device1", {})
            mac = dev.get("Address")
            name = dev.get("Name")
            mac_s = mac.value if mac else ""
            return mac_s, (name.value if name else mac_s or "Device")
    return "", "Device"


class _PairingAgent(ServiceInterface):
    """org.bluez.Agent1 — see https://github.com/bluez/bluez/blob/master/doc/agent-api.txt.
    Registered with capability "KeyboardDisplay" (we can both show a passkey
    and accept typed input), which is the only capability covering every
    callback below.
    """

    def __init__(self) -> None:
        super().__init__("org.bluez.Agent1")

    async def _wait(self, path: str, kind: str, passkey: int | None = None) -> dict | None:
        global _pending
        mac, name = await _device_info(path)
        req = _PendingRequest(mac=mac, name=name, kind=kind, passkey=passkey)
        _pending = req
        try:
            await asyncio.wait_for(req.event.wait(), timeout=60)
        except asyncio.TimeoutError:
            pass
        finally:
            if _pending is req:
                _pending = None
        return req.response

    @method()
    def Release(self):
        pass

    @method()
    async def RequestPinCode(self, device: "o") -> "s":
        resp = await self._wait(device, "pin")
        if not resp or not resp.get("value"):
            raise DBusError("org.bluez.Error.Rejected", "No PIN entered")
        return resp["value"]

    @method()
    def DisplayPinCode(self, device: "o", pincode: "s"):
        pass

    @method()
    async def RequestPasskey(self, device: "o") -> "u":
        resp = await self._wait(device, "passkey")
        if not resp or not resp.get("value"):
            raise DBusError("org.bluez.Error.Rejected", "No passkey entered")
        try:
            return int(resp["value"])
        except ValueError:
            raise DBusError("org.bluez.Error.Rejected", "Invalid passkey")

    @method()
    def DisplayPasskey(self, device: "o", passkey: "u", entered: "q"):
        # Informational only: the user types this on the OTHER device (one
        # with no screen of its own), not here, so there's no response to
        # collect — just something for the Bluetooth page to show.
        global _pending
        _pending = _PendingRequest(mac="", name="", kind="display", passkey=passkey)

    @method()
    async def RequestConfirmation(self, device: "o", passkey: "u"):
        resp = await self._wait(device, "confirm", passkey=passkey)
        if not resp or not resp.get("accept"):
            raise DBusError("org.bluez.Error.Rejected", "Rejected")

    @method()
    async def RequestAuthorization(self, device: "o"):
        resp = await self._wait(device, "authorize")
        if not resp or not resp.get("accept"):
            raise DBusError("org.bluez.Error.Rejected", "Rejected")

    @method()
    def AuthorizeService(self, device: "o", uuid: "s"):
        # Auto-approved: by the time BlueZ asks this, the device is already
        # trusted (connect() below calls set_trusted(True) right after
        # pairing) — prompting again per-service would just be noise with no
        # real security benefit on a single-user home PC.
        pass

    @method()
    def Cancel(self):
        global _pending
        if _pending:
            _pending.event.set()


async def _ensure_agent() -> None:
    global _agent_registered
    if _agent_registered:
        return
    bus = await _get_bus()
    bus.export(AGENT_PATH, _PairingAgent())
    manager = (await _proxy("/org/bluez")).get_interface("org.bluez.AgentManager1")
    try:
        await manager.call_register_agent(AGENT_PATH, "KeyboardDisplay")
    except Exception:
        pass  # already registered — e.g. a previous backend crash never unregistered it
    try:
        await manager.call_request_default_agent(AGENT_PATH)
    except Exception:
        pass
    _agent_registered = True


def pairing_request() -> dict | None:
    if not _pending:
        return None
    return {"mac": _pending.mac, "name": _pending.name, "kind": _pending.kind, "passkey": _pending.passkey}


async def respond_pairing_request(value: str | None = None, accept: bool | None = None) -> bool:
    if not _pending:
        return False
    _pending.response = {"value": value, "accept": accept}
    _pending.event.set()
    return True


async def _adapter_path() -> str | None:
    for path, ifaces in (await _managed_objects()).items():
        if "org.bluez.Adapter1" in ifaces:
            return path
    return None


async def get_state(scan: bool = False) -> dict:
    adapter_path = await _adapter_path()
    if not adapter_path:
        return {
            "available": False,
            "error": "This PC has no Bluetooth adapter. Plug in a USB Bluetooth adapter to use Bluetooth.",
        }
    adapter = (await _proxy(adapter_path)).get_interface("org.bluez.Adapter1")
    powered = await adapter.get_powered()

    if scan and powered:
        try:
            await adapter.call_start_discovery()
            await asyncio.sleep(8)
        except Exception:
            pass
        finally:
            try:
                await adapter.call_stop_discovery()
            except Exception:
                pass

    devices = []
    for path, ifaces in (await _managed_objects()).items():
        dev = ifaces.get("org.bluez.Device1")
        if not dev or not path.startswith(adapter_path):
            continue
        name = dev.get("Name")
        mac = dev.get("Address")
        paired = dev.get("Paired")
        if not paired and not name:
            continue  # unnamed, unpaired devices are just MAC-address noise
        devices.append(
            {
                "mac": mac.value if mac else "",
                "name": name.value if name else "",
                "paired": bool(paired.value) if paired else False,
                "connected": bool(dev["Connected"].value) if "Connected" in dev else False,
            }
        )
    devices.sort(key=lambda d: (not d["connected"], not d["paired"], d["name"].lower()))
    return {"available": True, "powered": powered, "devices": devices[:25]}


async def set_power(on: bool) -> tuple[bool, str]:
    adapter_path = await _adapter_path()
    if not adapter_path:
        return False, "This PC has no Bluetooth adapter."
    adapter = (await _proxy(adapter_path)).get_interface("org.bluez.Adapter1")
    await adapter.set_powered(on)
    return True, ""


async def _device_path(mac: str) -> str | None:
    for path, ifaces in (await _managed_objects()).items():
        dev = ifaces.get("org.bluez.Device1")
        if dev and dev.get("Address") and dev["Address"].value == mac:
            return path
    return None


async def connect(mac: str, name: str) -> tuple[bool, str]:
    path = await _device_path(mac)
    if not path:
        return False, "Unknown device."
    await _ensure_agent()
    device = (await _proxy(path)).get_interface("org.bluez.Device1")
    try:
        if not await device.get_paired():
            await device.call_pair()
        await device.set_trusted(True)
        await device.call_connect()
        return True, f"{name} connected."
    except Exception:
        return False, f"Couldn't connect to {name}. Make sure it's on and nearby."


async def disconnect(mac: str, name: str) -> tuple[bool, str]:
    path = await _device_path(mac)
    if not path:
        return False, "Unknown device."
    device = (await _proxy(path)).get_interface("org.bluez.Device1")
    try:
        await device.call_disconnect()
        return True, f"{name} disconnected."
    except Exception:
        return False, f"Couldn't disconnect {name}."


async def forget(mac: str, name: str) -> tuple[bool, str]:
    adapter_path = await _adapter_path()
    path = await _device_path(mac)
    if not adapter_path or not path:
        return False, "Unknown device."
    adapter = (await _proxy(adapter_path)).get_interface("org.bluez.Adapter1")
    try:
        await adapter.call_remove_device(path)
        return True, f"Forgot {name}."
    except Exception:
        return False, f"Couldn't forget {name}."
