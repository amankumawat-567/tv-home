from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import config
from .routes import bluetooth, display, misc, power, sound, state, wifi

app = FastAPI(title="TV Home", version=config.VERSION)

for router in (state.router, wifi.router, bluetooth.router, sound.router, display.router, power.router, misc.router):
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
