from fastapi import APIRouter

from ..models import BtDeviceBody, BtPairingRespondBody, BtPowerBody
from ..providers import bluetooth_provider
from .state import broadcast_state

router = APIRouter(prefix="/api/bluetooth")


@router.get("")
async def get_bluetooth(scan: int = 0):
    return await bluetooth_provider.get_state(scan=bool(scan))


@router.get("/pairing")
async def get_pairing_request():
    # Polled by the Bluetooth page while a connect() call is in flight, since
    # that call blocks for the whole pairing handshake -- this is how the UI
    # learns a PIN/passkey prompt is needed partway through, not just after.
    return bluetooth_provider.pairing_request()


@router.post("/pairing/respond")
async def respond_pairing(body: BtPairingRespondBody):
    ok = await bluetooth_provider.respond_pairing_request(body.value, body.accept)
    return {"ok": ok}


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
