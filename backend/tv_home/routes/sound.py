from fastapi import APIRouter

from ..models import SoundActionBody
from ..providers import sound_provider
from .state import broadcast_state

router = APIRouter(prefix="/api/sound")


@router.get("")
async def get_sound():
    return await sound_provider.get_state()


@router.post("")
async def sound_action(body: SoundActionBody):
    ok, message = await sound_provider.action(body.action, body.id)
    await broadcast_state()
    return {"ok": ok, "message": message}
