"""Real Power backend: dbus-fast talking to logind for sleep/restart/shutdown,
per the PRD's stack table. "desktop" doesn't go through logind — it closes TV
Home's own shell window and leaves a sentinel file; session/tv-home-session.sh
notices the window exiting, checks the sentinel, and execs the regular XFCE
desktop instead of restarting TV Home.

Sleep/restart/shutdown need a polkit rule granting the TV Home user
passwordless use of logind's power actions — session/install.sh installs
session/polkit/46-tv-home.rules for exactly this; without it, `call_suspend`/
`call_reboot`/`call_power_off` raise a D-Bus AccessDenied/NotAuthorized error
(interactive=False below means logind reports that immediately rather than
waiting on an auth dialog nothing here could answer).

NOT RUNNABLE OR TESTED on this macOS sandbox (no D-Bus system bus / logind
here) — written to spec; verify on the real PC.
"""
import sys

from dbus_fast.aio import MessageBus
from dbus_fast.constants import BusType

from .. import chrome
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
    if kind == "desktop":
        DESKTOP_SENTINEL.parent.mkdir(parents=True, exist_ok=True)
        DESKTOP_SENTINEL.touch()
        # Closing the shell window (not exiting this process) is what lets
        # tv-home-session.sh's foreground wait on it return and act on the
        # sentinel — see chrome.close_shell()'s own docstring for why killing
        # the backend alone (the old, broken approach) never worked.
        chrome.close_shell()
        return True, "Going to the desktop"

    if kind not in ("sleep", "restart", "poweroff"):
        return False, "Unknown action."

    method = {"sleep": "call_suspend", "restart": "call_reboot", "poweroff": "call_power_off"}[kind]
    try:
        manager = await _manager()
        await getattr(manager, method)(False)
        return True, ""
    except Exception as exc:
        print(f"[tv_home.system.power] {kind} failed: {exc}", file=sys.stderr)
        if "AccessDenied" in str(exc) or "NotAuthorized" in str(exc) or "InteractionRequired" in str(exc):
            return False, "Not allowed — check the polkit rule is installed (session/polkit/46-tv-home.rules)."
        return False, "Couldn't complete that action."
