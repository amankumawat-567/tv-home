"""Phone-typing (I2): scan a QR code on the TV, type on your phone instead of
hunting across the on-screen keyboard. A session is just a short-lived token
mapping to whatever's been typed so far — the TV polls it, the phone posts to
it, and the actual QWERTY grid never enters the picture for this path.

In-memory only (not settings.json): these are seconds-to-minutes-lived, not a
preference, and don't need to survive a backend restart.
"""
import secrets
import time
from typing import Optional

SESSION_TTL_SECONDS = 10 * 60

_sessions: dict[str, dict] = {}


def _prune() -> None:
    now = time.monotonic()
    expired = [t for t, s in _sessions.items() if now - s["created"] > SESSION_TTL_SECONDS]
    for t in expired:
        _sessions.pop(t, None)


def start() -> str:
    _prune()
    token = secrets.token_urlsafe(16)
    _sessions[token] = {"value": "", "done": False, "created": time.monotonic()}
    return token


def get(token: str) -> Optional[dict]:
    session = _sessions.get(token)
    if not session:
        return None
    return {"value": session["value"], "done": session["done"]}


def set_value(token: str, value: str) -> bool:
    session = _sessions.get(token)
    if not session:
        return False
    session["value"] = value
    return True


def mark_done(token: str) -> bool:
    session = _sessions.get(token)
    if not session:
        return False
    session["done"] = True
    return True


def end(token: str) -> None:
    _sessions.pop(token, None)
