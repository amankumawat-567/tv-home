import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .. import apps, chrome, clock, events, info
from ..models import InstallBody, MoveBody
from ..providers import bluetooth_provider, display_provider, sound_provider, wifi_provider
from ..wallpaper import current_wallpaper

router = APIRouter()


def _wifi_bars(wifi_state: dict) -> str | int:
    if not wifi_state.get("wifiOn"):
        return "off"
    active = next((n for n in wifi_state.get("networks", []) if n["active"]), None)
    if not active:
        return "none"
    return max(1, min(4, round(active["signal"] / 25)))


def _bluetooth_status(bt_state: dict) -> str:
    if not bt_state.get("available") or not bt_state.get("powered"):
        return "off"
    if any(d["connected"] for d in bt_state.get("devices", [])):
        return "connected"
    return "on"


async def build_state() -> dict:
    wifi_state, bt_state, sound_state, clock_state = await asyncio.gather(
        wifi_provider.get_state(), bluetooth_provider.get_state(), sound_provider.get_state(), asyncio.to_thread(clock.get_state)
    )
    return {
        "user": info.display_name(),
        "wallpaper": current_wallpaper() is not None,
        "apps": apps.apps_view(),
        "catalog": apps.catalog_view(),
        "status": {
            "wifi": _wifi_bars(wifi_state),
            "bluetooth": _bluetooth_status(bt_state),
            "volume": sound_state.get("volume", 0),
            "muted": sound_state.get("muted", False),
            "clockWrong": clock_state["clockWrong"],
        },
    }


async def broadcast_state() -> None:
    events.publish_state(await build_state())


@router.get("/api/state")
async def get_state():
    return await build_state()


@router.websocket("/api/events")
async def ws_events(websocket: WebSocket):
    await websocket.accept()
    queue = events.bus.subscribe()
    try:
        await websocket.send_json({"type": "state", "data": await build_state()})
        while True:
            event = await queue.get()
            await websocket.send_json(event)
    except WebSocketDisconnect:
        pass
    finally:
        events.bus.unsubscribe(queue)


@router.post("/api/home")
async def post_home():
    ok, message = chrome.go_home()
    events.publish_running(None)
    # Only Home counts as "idle" — re-arm whatever screen-off timer Settings >
    # Display is set to (see display_provider.inhibit() below for why).
    await display_provider.restore()
    return {"ok": ok, "message": message}


@router.post("/api/apps/{app_id}/launch")
async def launch_app(app_id: str):
    ok, message = chrome.launch(app_id)
    if ok:
        app = next((a for a in apps.load_apps() if a["id"] == app_id), None)
        if app:
            events.publish_running({"id": app["id"], "name": app["name"]})
        # An app owns the screen now — suspend the idle screen-off timer so a
        # long movie with no remote input doesn't get blanked mid-playback.
        await display_provider.inhibit()
    return {"ok": ok, "message": message}


@router.post("/api/apps")
async def install_app(body: InstallBody):
    ok, message = apps.install_from_catalog(body.id) if body.id and not body.url else apps.install(body.name, body.url, body.ua, body.id)
    await broadcast_state()
    return {"ok": ok, "message": message, **(await build_state())}


@router.delete("/api/apps/{app_id}")
async def remove_app(app_id: str):
    ok, message = apps.remove(app_id)
    await broadcast_state()
    return {"ok": ok, "message": message, **(await build_state())}


@router.post("/api/apps/{app_id}/move")
async def move_app(app_id: str, body: MoveBody):
    ok, message = apps.move(app_id, body.dir)
    await broadcast_state()
    return {"ok": ok, "message": message, **(await build_state())}
