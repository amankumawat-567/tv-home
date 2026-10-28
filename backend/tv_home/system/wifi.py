"""Real Wi-Fi backend: dbus-fast talking to NetworkManager, per the PRD's stack
table (chosen over v1's nmcli-wrapping for live change events instead of
polling CLI output).

NOT RUNNABLE OR TESTED on this macOS sandbox (no D-Bus system bus or
NetworkManager here) — written to spec against NetworkManager's documented
D-Bus API; verify end-to-end on the real PC (join a WPA2 network, wrong
password, forget).
"""
import asyncio

from dbus_fast import Variant
from dbus_fast.aio import MessageBus
from dbus_fast.constants import BusType

NM_SERVICE = "org.freedesktop.NetworkManager"
NM_PATH = "/org/freedesktop/NetworkManager"
DEVICE_TYPE_WIFI = 2
NM_DEVICE_STATE_ACTIVATED = 100

_bus: MessageBus | None = None


async def _get_bus() -> MessageBus:
    global _bus
    if _bus is None:
        _bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
    return _bus


async def _proxy(path: str, service: str = NM_SERVICE):
    bus = await _get_bus()
    introspection = await bus.introspect(service, path)
    return bus.get_proxy_object(service, path, introspection)


async def _wifi_device_path() -> str | None:
    nm = (await _proxy(NM_PATH)).get_interface(NM_SERVICE)
    for path in await nm.get_all_devices():
        dev = (await _proxy(path)).get_interface(f"{NM_SERVICE}.Device")
        if await dev.get_device_type() == DEVICE_TYPE_WIFI:
            return path
    return None


def _decode_ssid(ssid_bytes) -> str:
    return bytes(ssid_bytes).decode("utf-8", errors="replace")


async def get_state(scan: bool = False) -> dict:
    nm = (await _proxy(NM_PATH)).get_interface(NM_SERVICE)
    wifi_enabled = await nm.get_wireless_enabled()
    dev_path = await _wifi_device_path()
    if not dev_path:
        return {"available": True, "wifiOn": wifi_enabled, "ethernet": False, "ip": "", "networks": []}

    dev_obj = await _proxy(dev_path)
    dev = dev_obj.get_interface(f"{NM_SERVICE}.Device")
    wireless = dev_obj.get_interface(f"{NM_SERVICE}.Device.Wireless")
    if scan:
        try:
            await wireless.call_request_scan({})
            await asyncio.sleep(3)
        except Exception:
            pass
    state = await dev.get_state()
    active_ap_path = await wireless.get_active_access_point()

    active_ssid = None
    if active_ap_path and active_ap_path != "/":
        ap = (await _proxy(active_ap_path)).get_interface(f"{NM_SERVICE}.AccessPoint")
        active_ssid = _decode_ssid(await ap.get_ssid())

    settings = (await _proxy("/org/freedesktop/NetworkManager/Settings")).get_interface(f"{NM_SERVICE}.Settings")
    saved_ssids: set[str] = set()
    for conn_path in await settings.call_list_connections():
        conn = (await _proxy(conn_path)).get_interface(f"{NM_SERVICE}.Settings.Connection")
        cfg = await conn.call_get_settings()
        wifi_cfg = cfg.get("802-11-wireless", {})
        ssid_variant = wifi_cfg.get("ssid")
        if ssid_variant:
            saved_ssids.add(_decode_ssid(ssid_variant.value))

    seen: dict[str, dict] = {}
    for ap_path in await wireless.call_get_all_access_points():
        ap = (await _proxy(ap_path)).get_interface(f"{NM_SERVICE}.AccessPoint")
        ssid = _decode_ssid(await ap.get_ssid())
        if not ssid:
            continue
        flags = await ap.get_flags()
        wpa_flags = await ap.get_wpa_flags()
        rsn_flags = await ap.get_rsn_flags()
        entry = {
            "ssid": ssid,
            "signal": await ap.get_strength(),
            "secure": bool(flags or wpa_flags or rsn_flags),
            "active": ssid == active_ssid,
            "saved": ssid in saved_ssids,
        }
        prev = seen.get(ssid)
        if not prev or (not prev["active"] and (entry["active"] or entry["signal"] > prev["signal"])):
            seen[ssid] = entry

    networks = sorted(seen.values(), key=lambda n: (not n["active"], not n["saved"], -n["signal"]))[:20]
    ip = ""
    if state == NM_DEVICE_STATE_ACTIVATED:
        ip4_path = await dev.get_ip4_config()
        if ip4_path and ip4_path != "/":
            ip4 = (await _proxy(ip4_path)).get_interface(f"{NM_SERVICE}.IP4Config")
            addresses = await ip4.get_address_data()
            if addresses:
                ip = addresses[0].get("address", Variant("s", "")).value

    return {"available": True, "wifiOn": wifi_enabled, "ethernet": False, "ip": ip, "networks": networks}


async def set_radio(on: bool) -> tuple[bool, str]:
    nm = (await _proxy(NM_PATH)).get_interface(NM_SERVICE)
    await nm.set_wireless_enabled(on)
    return True, ""


def _nm_error(message: str) -> str:
    m = message.lower()
    if "secrets" in m or "psk" in m or "password" in m:
        return "Wrong or missing password."
    if "not authorized" in m:
        return "This change needs permission. Try it from the desktop."
    if "no network with ssid" in m:
        return "That network is out of range."
    return "Something went wrong."


async def connect(ssid: str, password: str | None, saved: bool) -> tuple[bool, str]:
    dev_path = await _wifi_device_path()
    if not dev_path:
        return False, "No Wi-Fi adapter found."
    nm = (await _proxy(NM_PATH)).get_interface(NM_SERVICE)
    try:
        if saved:
            settings = (await _proxy("/org/freedesktop/NetworkManager/Settings")).get_interface(f"{NM_SERVICE}.Settings")
            conn_path = None
            for path in await settings.call_list_connections():
                conn = (await _proxy(path)).get_interface(f"{NM_SERVICE}.Settings.Connection")
                cfg = await conn.call_get_settings()
                ssid_variant = cfg.get("802-11-wireless", {}).get("ssid")
                if ssid_variant and _decode_ssid(ssid_variant.value) == ssid:
                    conn_path = path
                    break
            if not conn_path:
                return False, "That network is out of range."
            await nm.call_activate_connection(conn_path, dev_path, "/")
        else:
            conn_settings: dict = {
                "connection": {"id": Variant("s", ssid), "type": Variant("s", "802-11-wireless")},
                "802-11-wireless": {"ssid": Variant("ay", ssid.encode()), "mode": Variant("s", "infrastructure")},
            }
            if password:
                conn_settings["802-11-wireless-security"] = {
                    "key-mgmt": Variant("s", "wpa-psk"),
                    "psk": Variant("s", password),
                }
            await nm.call_add_and_activate_connection(conn_settings, dev_path, "/")
        return True, f"Connected to {ssid}."
    except Exception as exc:  # dbus-fast raises DBusError subclasses with .text
        return False, _nm_error(getattr(exc, "text", str(exc)))


async def forget(ssid: str) -> tuple[bool, str]:
    settings = (await _proxy("/org/freedesktop/NetworkManager/Settings")).get_interface(f"{NM_SERVICE}.Settings")
    for path in await settings.call_list_connections():
        conn_obj = await _proxy(path)
        conn = conn_obj.get_interface(f"{NM_SERVICE}.Settings.Connection")
        cfg = await conn.call_get_settings()
        ssid_variant = cfg.get("802-11-wireless", {}).get("ssid")
        if ssid_variant and _decode_ssid(ssid_variant.value) == ssid:
            await conn.call_delete()
            return True, f"Forgot {ssid}."
    return False, "That network isn't saved."
