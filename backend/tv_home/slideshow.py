"""Advances the wallpaper on a timer when Settings > Wallpaper > Slideshow is
on — started as a background task from main.py's lifespan. Re-checks whether
it's still enabled every minute rather than once at startup, so turning it
off takes effect without a restart and a changed interval is picked up on
its next tick."""
import asyncio

from . import wallpaper
from .events import publish_state

CHECK_INTERVAL_SECONDS = 60


async def run(build_state) -> None:
    elapsed_minutes = 0
    while True:
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
        elapsed_minutes += 1
        settings = wallpaper.slideshow_settings()
        if not settings["enabled"]:
            elapsed_minutes = 0
            continue
        if elapsed_minutes >= max(1, settings["minutes"]):
            elapsed_minutes = 0
            wallpaper.next_wallpaper()
            publish_state(await build_state())
