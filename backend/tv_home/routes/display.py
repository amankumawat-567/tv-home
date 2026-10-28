import asyncio

from fastapi import APIRouter

from ..models import DisplayConfirmBody, DisplaySetBody, ScreenOffBody
from ..providers import display_provider
from .state import broadcast_state

router = APIRouter(prefix="/api/display")

REVERT_SECONDS = 15


@router.get("")
async def get_display():
    return await display_provider.get_state()


@router.post("")
async def set_mode(body: DisplaySetBody):
    ok, result = await display_provider.set_mode(body.id)
    if not ok:
        return {"ok": False, "token": ""}
    token = result

    async def auto_revert():
        await asyncio.sleep(REVERT_SECONDS)
        await display_provider.revert_if_unconfirmed(token)
        await broadcast_state()

    asyncio.create_task(auto_revert())
    return {"ok": True, "token": token}


@router.post("/confirm")
async def confirm_mode(body: DisplayConfirmBody):
    ok = await display_provider.confirm_mode(body.token)
    await broadcast_state()
    return {"ok": ok}


@router.post("/screen-off")
async def screen_off(body: ScreenOffBody):
    ok, message = await display_provider.set_screen_off(body.minutes)
    return {"ok": ok, "message": message}
