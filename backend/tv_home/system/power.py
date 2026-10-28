"""Real Power backend: dbus-fast talking to logind for sleep/restart/shutdown,
per the PRD's stack table. "desktop" doesn't go through logind — it leaves the
TV session for the regular XFCE desktop; see session/tv-home-session.sh, which
polls for the sentinel file this writes and execs the normal desktop session
instead of restarting TV Home when it finds one.

NOT RUNNABLE OR TESTED on this macOS sandbox (no D-Bus system bus / logind
here) — written to spec; verify on the real PC.
"""
import os
import threading

from dbus_fast.aio import MessageBus
from dbus_fast.constants import BusType

from ..config import APPDIR

LOGIND = "org.freedesktop.login1"
LOGIND_PATH = "/org/freedesktop/login1"
DESKTOP_SENTINEL = APPDIR / "go-desktop"

_bus: MessageBus | None = None


async def _manager():
    global _bus
    if _bus is None:
        _bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
    introspection = await _bus.introspect(LOGIND, LOGIND_PATH)
    proxy = _bus.get_proxy_object(LOGIND, LOGIND_PATH, introspection)
    return proxy.get_interface(f"{LOGIND}.Manager")


async def action(kind: str) -> tuple[bool, str]:
    try:
        if kind == "sleep":
            await (await _manager()).call_suspend(False)
            return True, ""
        if kind == "restart":
            await (await _manager()).call_reboot(False)
            return True, ""
        if kind == "poweroff":
            await (await _manager()).call_power_off(False)
            return True, ""
        if kind == "desktop":
            DESKTOP_SENTINEL.parent.mkdir(parents=True, exist_ok=True)
            DESKTOP_SENTINEL.touch()
            # Exit shortly after responding; the session script's supervision
            # loop notices the sentinel and execs the normal desktop instead
            # of restarting TV Home (see session/tv-home-session.sh).
            threading.Timer(0.5, lambda: os._exit(0)).start()
            return True, "Going to the desktop"
        return False, "Unknown action."
    except Exception:
        return False, "Couldn't complete that action."
