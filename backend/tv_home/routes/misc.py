import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from .. import clock, config, info
from ..models import SlideshowBody, WallpaperSetBody
from ..wallpaper import current_wallpaper, next_wallpaper, set_slideshow, set_wallpaper, slideshow_settings, wallpaper_list, wallpapers
from .state import broadcast_state

router = APIRouter()

_MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
# The resource at a fixed URL (the current wallpaper) changes without the URL
# itself changing, so it must never be cached — otherwise switching
# wallpapers can silently show the old image until a hard refresh (this was
# reported as "wallpapers aren't visible/switchable").
_NO_STORE = {"Cache-Control": "no-store"}


@router.get("/api/about")
async def get_about():
    return info.about()


@router.get("/api/datetime")
async def get_datetime():
    return clock.get_state()


@router.post("/api/wallpaper")
async def post_wallpaper():
    next_wallpaper()
    await broadcast_state()
    return {"ok": True}


@router.get("/api/wallpaper/list")
async def get_wallpaper_list():
    return wallpaper_list()


@router.post("/api/wallpaper/set")
async def post_wallpaper_set(body: WallpaperSetBody):
    set_wallpaper(body.index)
    await broadcast_state()
    return wallpaper_list()


@router.get("/api/wallpaper/slideshow")
async def get_wallpaper_slideshow():
    return slideshow_settings()


@router.post("/api/wallpaper/slideshow")
async def post_wallpaper_slideshow(body: SlideshowBody):
    return set_slideshow(body.enabled, body.minutes)


@router.get("/wallpaper")
async def get_wallpaper():
    wall = current_wallpaper()
    if not wall:
        raise HTTPException(404, "No wallpaper configured.")
    return FileResponse(wall, media_type=_MIME.get(wall.suffix.lower(), "image/jpeg"), headers=_NO_STORE)


@router.get("/wallpaper/{index}")
async def get_wallpaper_by_index(index: int):
    # Thumbnails for the gallery in Settings > Wallpaper -- unlike /wallpaper
    # above, the content at a given index never changes, so this is safe to
    # cache normally.
    walls = wallpapers()
    if index < 0 or index >= len(walls):
        raise HTTPException(404, "No such wallpaper.")
    wall = walls[index]
    return FileResponse(wall, media_type=_MIME.get(wall.suffix.lower(), "image/jpeg"))


@router.get("/icons/{name}")
async def get_icon(name: str):
    if not re.fullmatch(r"[a-z0-9-]+\.png", name):
        raise HTTPException(404, "Not found")
    path = config.ICONS / name
    if not path.exists():
        raise HTTPException(404, "Not found")
    return FileResponse(path, media_type="image/png")
