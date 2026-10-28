"""Fake updater used when TV_HOME_MOCK=1 — never touches the network or the
filesystem, so the About page's update flow is testable without a real
GitHub release to check against."""
import asyncio

from ..config import VERSION

_state = {"applied": False}


async def check_latest() -> dict:
    if _state["applied"]:
        return {"current": VERSION, "latest": VERSION, "available": False, "url": None, "notes": ""}
    return {
        "current": VERSION,
        "latest": "2.1.0",
        "available": True,
        "url": "https://example.com/tv-home-2.1.0.tar.gz",
        "notes": "(mock) Example release notes — this is fake data from mock/update.py.",
    }


async def apply_update(url: str) -> tuple[bool, str]:
    if not url:
        return False, "No update package available."
    await asyncio.sleep(1)
    _state["applied"] = True
    return True, "(mock) Would download and install the update, then restart."
