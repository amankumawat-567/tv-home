import os
from pathlib import Path

HOME = Path.home()
APPDIR = HOME / ".config/tv-home"
APPS_FILE = APPDIR / "apps.json"
SETTINGS_FILE = APPDIR / "settings.json"
ICONS = APPDIR / "icons"
PROFILE = APPDIR / "chrome-profile"
USER_WALLS = APPDIR / "wallpapers"
WALL_DIRS = [USER_WALLS, Path("/usr/share/xfce4/backdrops"), Path("/usr/share/backgrounds")]

# The GitHub repo releases are published to — used by update.py to check for
# and fetch new versions (Y6). Change this if you fork/republish elsewhere.
GITHUB_REPO = "amankumawat-567/tv-home"

# Where this install lives: a release tarball's layout (VERSION at the repo
# root, backend/ and frontend/dist/ beside it) when installed by
# session/install.sh, or the source checkout during development.
INSTALL_ROOT = Path(__file__).resolve().parents[2]
_VERSION_FILE = INSTALL_ROOT / "VERSION"
VERSION = _VERSION_FILE.read_text().strip() if _VERSION_FILE.exists() else "0.0.0-dev"

# Mock mode fakes Wi-Fi/Bluetooth/Sound/Display/Power so the whole UI runs on a
# laptop with no NetworkManager, BlueZ, PipeWire or X11 in sight (see
# backend/README.md and the PRD's M0 "Done when").
MOCK = os.environ.get("TV_HOME_MOCK") == "1"

CATALOG = [
    {"id": "netflix", "name": "Netflix", "url": "https://www.netflix.com", "cat": "Movies & TV"},
    {"id": "jiohotstar", "name": "JioHotstar", "url": "https://www.hotstar.com/in", "cat": "Movies & TV"},
    {"id": "primevideo", "name": "Prime Video", "url": "https://www.primevideo.com", "cat": "Movies & TV"},
    {"id": "sonyliv", "name": "SonyLIV", "url": "https://www.sonyliv.com", "cat": "Movies & TV"},
    {"id": "zee5", "name": "ZEE5", "url": "https://www.zee5.com", "cat": "Movies & TV"},
    {"id": "appletv", "name": "Apple TV", "url": "https://tv.apple.com", "cat": "Movies & TV"},
    {"id": "crunchyroll", "name": "Crunchyroll", "url": "https://www.crunchyroll.com", "cat": "Anime"},
    {
        "id": "youtube",
        "name": "YouTube",
        "url": "https://www.youtube.com/tv",
        "cat": "Videos",
        "ua": (
            "Mozilla/5.0 (Linux; Tizen 2.3; SmartHub; SMART-TV; SmartTV; U; Maple2012) "
            "AppleWebKit/538.1+ (KHTML, like Gecko) TV Safari/538.1+"
        ),
    },
    {"id": "twitch", "name": "Twitch", "url": "https://www.twitch.tv", "cat": "Videos"},
    {"id": "spotify", "name": "Spotify", "url": "https://open.spotify.com", "cat": "Music"},
    {"id": "ytmusic", "name": "YouTube Music", "url": "https://music.youtube.com", "cat": "Music"},
    {"id": "jiosaavn", "name": "JioSaavn", "url": "https://www.jiosaavn.com", "cat": "Music"},
]
