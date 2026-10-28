import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from .. import clock, info
from ..config import ICONS
from ..wallpaper import current_wallpaper, next_wallpaper

router = APIRouter()

_MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}


@router.get("/api/about")
async def get_about():
    return info.about()


@router.get("/api/datetime")
async def get_datetime():
    return clock.get_state()


@router.post("/api/wallpaper")
async def post_wallpaper():
    next_wallpaper()
    return {"ok": True}


@router.get("/wallpaper")
async def get_wallpaper():
    wall = current_wallpaper()
    if not wall:
        raise HTTPException(404, "No wallpaper configured.")
    return FileResponse(wall, media_type=_MIME.get(wall.suffix.lower(), "image/jpeg"))


@router.get("/icons/{name}")
async def get_icon(name: str):
    if not re.fullmatch(r"[a-z0-9-]+\.png", name):
        raise HTTPException(404, "Not found")
    path = ICONS / name
    if not path.exists():
        raise HTTPException(404, "Not found")
    return FileResponse(path, media_type="image/png")
