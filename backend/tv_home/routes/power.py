from fastapi import APIRouter

from .. import chrome
from ..models import PowerBody
from ..providers import power_provider

router = APIRouter(prefix="/api/power")


@router.post("")
async def power_action(body: PowerBody):
    if body.action in ("restart", "poweroff", "desktop"):
        chrome.go_home()
    ok, message = await power_provider.action(body.action)
    return {"ok": ok, "message": message}
