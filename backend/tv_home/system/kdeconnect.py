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
import json
from pathlib import Path

from dbus_fast import Message
from dbus_fast.aio import MessageBus
from dbus_fast.constants import BusType, MessageType

SERVICE = "org.kde.kdeconnect"
DAEMON_PATH = "/modules/kdeconnect"

# The "Run Command" plugin turns each entry below into a button on the
# phone's KDE Connect app -- a real D-pad remote, not just the generic
# trackpad "Remote input" plugin. Keysym names are X11's (what xdotool takes,
# and what a real keyboard's own Up/Down/.../Escape/Home keys already send),
# matched against frontend/src/state/keymap.ts's own DEFAULTS so these
# buttons work exactly like pressing those keys would -- including picking
# up the user's own remapping in Settings > Remote, since nothing here
# bypasses the frontend's normal key handling.
TV_REMOTE_COMMANDS: dict[str, dict[str, str]] = {
    "tv_up": {"name": "Up", "command": "xdotool key Up"},
    "tv_down": {"name": "Down", "command": "xdotool key Down"},
    "tv_left": {"name": "Left", "command": "xdotool key Left"},
    "tv_right": {"name": "Right", "command": "xdotool key Right"},
    "tv_select": {"name": "OK", "command": "xdotool key Return"},
    "tv_back": {"name": "Back", "command": "xdotool key Escape"},
    "tv_home": {"name": "Home", "command": "xdotool key Home"},
    "tv_menu": {"name": "Menu", "command": "xdotool key Menu"},
    "tv_vol_up": {"name": "Volume Up", "command": "xdotool key XF86AudioRaiseVolume"},
    "tv_vol_down": {"name": "Volume Down", "command": "xdotool key XF86AudioLowerVolume"},
    "tv_mute": {"name": "Mute", "command": "xdotool key XF86AudioMute"},
}

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


def _qsettings_escape(value: str) -> str:
    # Qt's QSettings INI format escapes exactly these two characters when a
    # string value is quoted -- verified by round-tripping a value with both
    # through a real QSettings instance (backslash first, so an escaped
    # backslash doesn't get re-escaped by the quote replacement after it).
    return value.replace("\\", "\\\\").replace('"', '\\"')


async def install_tv_remote(device_id: str) -> None:
    """Writes the TV_REMOTE_COMMANDS set into this device's "Run Command"
    plugin config, so the phone shows a real D-pad remote instead of (or
    alongside) the generic trackpad. Called right after pairing, not
    something the user has to set up by hand in KDE Connect's own app.

    The config format and path (~/.config/kdeconnect/<id>/kdeconnect_runcommand/
    config, a QSettings INI file with a single JSON-encoded "commands" string
    under [General]) come directly from kdeconnect-kde's own source
    (core/kdeconnectpluginconfig.cpp, models/commandsmodel.cpp) -- not
    guessed. Emits the same configChanged D-Bus signal
    KdeConnectPluginConfig::set() does, so an already-running kdeconnectd
    picks this up immediately instead of only on the next reconnect.
    """
    config_dir = Path.home() / ".config" / "kdeconnect" / device_id / "kdeconnect_runcommand"
    config_dir.mkdir(parents=True, exist_ok=True)
    commands_json = json.dumps(TV_REMOTE_COMMANDS, separators=(",", ":"))
    content = f'[General]\ncommands="{_qsettings_escape(commands_json)}"\n'
    (config_dir / "config").write_text(content)

    try:
        bus = await _get_bus()
        bus.send(
            Message(
                path=f"/kdeconnect/{device_id}/kdeconnect_runcommand",
                interface="org.kde.kdeconnect.config",
                member="configChanged",
                message_type=MessageType.SIGNAL,
            )
        )
    except Exception:
        pass  # config is on disk either way -- a later reconnect will pick it up


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
        # Pre-stage the TV remote config now rather than waiting for
        # acceptance -- harmless if the request is later rejected (it just
        # sits unused in a config directory for a device we don't talk to),
        # and it means the remote buttons are ready the instant the phone
        # does accept, with no race against its own reconnect/sendConfig().
        try:
            await install_tv_remote(device_id)
        except Exception:
            pass
        return True, f"Pairing request sent to {name} — accept it on your phone."
    except Exception:
        return False, f"Couldn't reach {name}."


async def accept(device_id: str, name: str) -> tuple[bool, str]:
    try:
        iface = await _device(device_id)
        await iface.call_accept_pairing()
        try:
            await install_tv_remote(device_id)
        except Exception:
            pass
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
