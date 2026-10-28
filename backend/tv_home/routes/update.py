from fastapi import APIRouter

from ..models import UpdateApplyBody
from ..providers import update_provider

router = APIRouter(prefix="/api/update")


@router.get("")
async def check():
    return await update_provider.check_latest()


@router.post("/apply")
async def apply(body: UpdateApplyBody):
    url = body.url
    if not url:
        latest = await update_provider.check_latest()
        url = latest.get("url")
    ok, message = await update_provider.apply_update(url)
    return {"ok": ok, "message": message}
