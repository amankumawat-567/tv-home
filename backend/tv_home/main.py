from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import config
from .providers import display_provider
from .routes import bluetooth, display, misc, power, sound, state, update, wifi


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # xset's timer doesn't survive a process restart the way our own
    # settings.json does — re-apply it so a configured screen-off minutes
    # takes effect immediately on boot, not only after the next Settings >
    # Display visit or app launch/close (see display_provider.restore()).
    await display_provider.restore()
    yield


app = FastAPI(title="TV Home", version=config.VERSION, lifespan=lifespan)

for router in (
    state.router,
    wifi.router,
    bluetooth.router,
    sound.router,
    display.router,
    power.router,
    update.router,
    misc.router,
):
    app.include_router(router)

# In production the backend also serves the built frontend (frontend/dist),
# so the whole thing is one process in one Chrome kiosk window pointed at
# http://127.0.0.1:PORT/ — see session/tv-home-session.sh. In dev, Vite serves
# the frontend itself and proxies /api, /icons, /wallpaper here instead.
_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _DIST.is_dir():
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="frontend")


def run() -> None:
    import uvicorn

    uvicorn.run("tv_home.main:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    run()
