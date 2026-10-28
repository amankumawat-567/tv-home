"""Fake Display backend used when TV_HOME_MOCK=1 — mirrors system/display.py
(xrandr)'s shape, including the 15s auto-revert confirmation token flow."""
import time
import uuid

_state = {"current": "1366x768", "screenOffMinutes": 10, "inhibited": False}
_MODES = ["1366x768", "1920x1080", "1280x720"]
_pending: dict[str, dict] = {}

REVERT_SECONDS = 15


async def get_state() -> dict:
    modes = [{"id": m, "label": f"{m} @ 60Hz", "current": m == _state["current"]} for m in _MODES]
    return {"available": True, "modes": modes, "screenOffMinutes": _state["screenOffMinutes"]}


async def set_mode(mode_id: str) -> tuple[bool, str]:
    if mode_id not in _MODES:
        return False, ""
    token = uuid.uuid4().hex
    _pending[token] = {"from": _state["current"], "to": mode_id, "at": time.monotonic()}
    _state["current"] = mode_id  # applied immediately; confirm makes it permanent
    return True, token


async def confirm_mode(token: str) -> bool:
    return _pending.pop(token, None) is not None


async def revert_if_unconfirmed(token: str) -> None:
    pending = _pending.pop(token, None)
    if pending:
        _state["current"] = pending["from"]


async def set_screen_off(minutes: int) -> tuple[bool, str]:
    _state["screenOffMinutes"] = minutes
    return True, ""


async def inhibit() -> None:
    # See system/display.py's inhibit(): suspends the screen-off timer while
    # an app is running, so it can't blank mid-movie.
    _state["inhibited"] = True


async def restore() -> None:
    _state["inhibited"] = False
