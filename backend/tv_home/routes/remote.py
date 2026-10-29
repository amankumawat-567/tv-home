from fastapi import APIRouter, HTTPException

from .. import keymap
from ..models import KeymapSetBody

router = APIRouter(prefix="/api/input")


@router.get("/keymap")
async def get_keymap():
    return keymap.get_keymap()


@router.post("/keymap")
async def set_keymap(body: KeymapSetBody):
    try:
        return keymap.set_key(body.action, body.key)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/keymap/reset")
async def reset_keymap():
    return keymap.reset()
