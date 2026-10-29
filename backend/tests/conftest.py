import os
import tempfile
from pathlib import Path

import pytest

os.environ["TV_HOME_MOCK"] = "1"


@pytest.fixture(autouse=True)
def isolated_config(monkeypatch):
    """Point every test at a throwaway ~/.config/tv-home so tests never touch
    the real user's data and don't leak state between tests.

    Every module reads these paths as `config.X` at call time (not
    `from .config import X` bound once at import) specifically so patching
    them here is enough on its own — no per-module patch needed. apps.py
    used to bind APPS_FILE/ICONS at import time and needed its own patch
    here too; that's what broke test isolation for wallpaper.py's
    SETTINGS_FILE later (same gotcha, different module) until both were
    switched to the call-time pattern."""
    with tempfile.TemporaryDirectory() as tmp:
        appdir = Path(tmp) / "tv-home"
        from tv_home import config

        monkeypatch.setattr(config, "APPDIR", appdir)
        monkeypatch.setattr(config, "APPS_FILE", appdir / "apps.json")
        monkeypatch.setattr(config, "SETTINGS_FILE", appdir / "settings.json")
        monkeypatch.setattr(config, "ICONS", appdir / "icons")
        monkeypatch.setattr(config, "PROFILE", appdir / "chrome-profile")
        monkeypatch.setattr(config, "USER_WALLS", appdir / "wallpapers")
        yield
