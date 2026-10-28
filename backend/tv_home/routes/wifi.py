from fastapi import APIRouter

from ..models import RadioBody, WifiConnectBody, WifiForgetBody
from ..providers import wifi_provider
from .state import broadcast_state

router = APIRouter(prefix="/api/wifi")


@router.get("")
async def get_wifi(scan: int = 0):
    return await wifi_provider.get_state(scan=bool(scan))


@router.post("/radio")
async def set_radio(body: RadioBody):
    ok, message = await wifi_provider.set_radio(body.on)
    await broadcast_state()
    return {"ok": ok, "message": message}


@router.post("/connect")
async def connect(body: WifiConnectBody):
    ok, message = await wifi_provider.connect(body.ssid, body.password, bool(body.saved))
    await broadcast_state()
    return {"ok": ok, "message": message}


@router.post("/forget")
async def forget(body: WifiForgetBody):
    ok, message = await wifi_provider.forget(body.ssid)
    await broadcast_state()
    return {"ok": ok, "message": message}
