"""Real Bluetooth backend: dbus-fast talking to BlueZ, per the PRD's stack table.

NOT RUNNABLE OR TESTED on this macOS sandbox (no D-Bus system bus or bluetoothd
here, and this PC has no Bluetooth adapter yet either) — written to spec against
BlueZ's documented D-Bus API; verify once a USB Bluetooth adapter is attached.
"""
import asyncio

from dbus_fast.aio import MessageBus
from dbus_fast.constants import BusType

BLUEZ = "org.bluez"

_bus: MessageBus | None = None


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
