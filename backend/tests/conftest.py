import os
import tempfile
from pathlib import Path

import pytest

os.environ["TV_HOME_MOCK"] = "1"


@pytest.fixture(autouse=True)
def isolated_config(monkeypatch):
    """Point every test at a throwaway ~/.config/tv-home so tests never touch
    the real user's data and don't leak state between tests."""
    with tempfile.TemporaryDirectory() as tmp:
        appdir = Path(tmp) / "tv-home"
        from tv_home import config

        monkeypatch.setattr(config, "APPDIR", appdir)
        monkeypatch.setattr(config, "APPS_FILE", appdir / "apps.json")
        monkeypatch.setattr(config, "SETTINGS_FILE", appdir / "settings.json")
        monkeypatch.setattr(config, "ICONS", appdir / "icons")
        monkeypatch.setattr(config, "PROFILE", appdir / "chrome-profile")
        monkeypatch.setattr(config, "USER_WALLS", appdir / "wallpapers")

        from tv_home import apps as apps_module

        monkeypatch.setattr(apps_module, "APPS_FILE", appdir / "apps.json")
        monkeypatch.setattr(apps_module, "ICONS", appdir / "icons")
        yield
