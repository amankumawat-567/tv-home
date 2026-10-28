"""Wallpaper selection, ported from v1's wallpapers()/current_wallpaper()."""
from pathlib import Path
from typing import Optional

from .config import SETTINGS_FILE, WALL_DIRS
from .state_store import read_json, write_json

IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".webp")


def wallpapers() -> list[Path]:
    found = []
    for d in WALL_DIRS:
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
    idx = read_json(SETTINGS_FILE, {}).get("wallpaper", 0)
    return walls[idx % len(walls)]


def next_wallpaper() -> None:
    settings = read_json(SETTINGS_FILE, {})
    settings["wallpaper"] = settings.get("wallpaper", 0) + 1
    write_json(SETTINGS_FILE, settings)
