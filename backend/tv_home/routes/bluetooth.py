from fastapi import APIRouter

from ..models import BtDeviceBody, BtPowerBody
from ..providers import bluetooth_provider
from .state import broadcast_state

router = APIRouter(prefix="/api/bluetooth")


@router.get("")
async def get_bluetooth(scan: int = 0):
    return await bluetooth_provider.get_state(scan=bool(scan))


@router.post("/power")
async def set_power(body: BtPowerBody):
    ok, message = await bluetooth_provider.set_power(body.on)
    await broadcast_state()
    return {"ok": ok, "message": message}


@router.post("/connect")
async def connect(body: BtDeviceBody):
    ok, message = await bluetooth_provider.connect(body.mac, body.name)
    await broadcast_state()
    return {"ok": ok, "message": message}


@router.post("/disconnect")
async def disconnect(body: BtDeviceBody):
    ok, message = await bluetooth_provider.disconnect(body.mac, body.name)
    await broadcast_state()
    return {"ok": ok, "message": message}


@router.post("/forget")
async def forget(body: BtDeviceBody):
    ok, message = await bluetooth_provider.forget(body.mac, body.name)
    await broadcast_state()
    return {"ok": ok, "message": message}
