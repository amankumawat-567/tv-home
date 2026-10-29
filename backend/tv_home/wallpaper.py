"""Wallpaper selection, ported from v1's wallpapers()/current_wallpaper()."""
from pathlib import Path
from typing import Optional

from . import config
from .state_store import read_json, write_json

IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".webp")
DEFAULT_SLIDESHOW_MINUTES = 15


def wallpapers() -> list[Path]:
    found = []
    for d in config.WALL_DIRS:
        if not d.is_dir():
            continue
        for p in sorted(d.rglob("*")):
            if (
                p.suffix.lower() in IMAGE_SUFFIXES
                and p.is_file()
                and p.stat().st_size > 100_000
                and len(p.relative_to(d).parts) <= 3
            ):
                found.append(p)
    return found


def current_wallpaper() -> Optional[Path]:
    walls = wallpapers()
    if not walls:
        return None
    idx = read_json(config.SETTINGS_FILE, {}).get("wallpaper", 0)
    return walls[idx % len(walls)]


def next_wallpaper() -> None:
    settings = read_json(config.SETTINGS_FILE, {})
    settings["wallpaper"] = settings.get("wallpaper", 0) + 1
    write_json(config.SETTINGS_FILE, settings)


def slideshow_settings() -> dict:
    settings = read_json(config.SETTINGS_FILE, {})
    return {
        "enabled": bool(settings.get("slideshowEnabled", False)),
        "minutes": int(settings.get("slideshowMinutes", DEFAULT_SLIDESHOW_MINUTES)),
    }


def set_slideshow(enabled: bool, minutes: Optional[int] = None) -> dict:
    settings = read_json(config.SETTINGS_FILE, {})
    settings["slideshowEnabled"] = enabled
    if minutes is not None and minutes > 0:
        settings["slideshowMinutes"] = minutes
    write_json(config.SETTINGS_FILE, settings)
    return slideshow_settings()
