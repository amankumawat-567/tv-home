from fastapi import APIRouter

from ..models import KdeConnectDeviceBody
from ..providers import kdeconnect_provider
from .state import broadcast_state

router = APIRouter(prefix="/api/kdeconnect")


@router.get("")
async def get_kdeconnect(refresh: int = 0):
    return await kdeconnect_provider.get_state(refresh=bool(refresh))


@router.post("/pair")
async def pair(body: KdeConnectDeviceBody):
    ok, message = await kdeconnect_provider.pair(body.id, body.name)
    await broadcast_state()
    return {"ok": ok, "message": message}


@router.post("/accept")
async def accept(body: KdeConnectDeviceBody):
    ok, message = await kdeconnect_provider.accept(body.id, body.name)
    await broadcast_state()
    return {"ok": ok, "message": message}


@router.post("/reject")
async def reject(body: KdeConnectDeviceBody):
    ok, message = await kdeconnect_provider.reject(body.id, body.name)
    await broadcast_state()
    return {"ok": ok, "message": message}


@router.post("/unpair")
async def unpair(body: KdeConnectDeviceBody):
    ok, message = await kdeconnect_provider.unpair(body.id, body.name)
    await broadcast_state()
    return {"ok": ok, "message": message}
