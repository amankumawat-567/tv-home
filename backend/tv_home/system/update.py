"""Real updater (Y6): checks GitHub Releases for a newer version and, if
asked, downloads and installs it by re-running session/install.sh against the
extracted release — the same installer a first-time install uses, so there's
only one place that logic lives.

`check_latest` is a plain HTTPS GET to a public API and works on any OS, so
it's actually runnable here (see below). `apply_update` modifies the real
install directory and restarts the backend via systemd, so it is NOT
RUNNABLE OR TESTED beyond that; it's written to spec — verify on the real PC.
"""
import asyncio
import json
import subprocess
import tarfile
import tempfile
import urllib.request
from pathlib import Path

from ..config import GITHUB_REPO, VERSION

API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def _parse_version(v: str) -> tuple[int, ...]:
    return tuple(int(p) for p in v.split(".") if p.isdigit())


def _fetch_latest() -> dict:
    req = urllib.request.Request(API_URL, headers={"Accept": "application/vnd.github+json", "User-Agent": "tv-home-backend"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


async def check_latest() -> dict:
    try:
        data = await asyncio.to_thread(_fetch_latest)
    except Exception:
        return {"current": VERSION, "latest": VERSION, "available": False, "url": None, "notes": "Couldn't reach GitHub to check for updates."}

    latest = (data.get("tag_name") or "").lstrip("v") or VERSION
    asset = next((a for a in data.get("assets", []) if a.get("name", "").endswith(".tar.gz")), None)
    try:
        available = _parse_version(latest) > _parse_version(VERSION)
    except ValueError:
        available = False
    return {
        "current": VERSION,
        "latest": latest,
        "available": available,
        "url": asset["browser_download_url"] if asset else None,
        "notes": (data.get("body") or "")[:500],
    }


def _download_extract_and_install(url: str) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tarball = Path(tmp) / "release.tar.gz"
        urllib.request.urlretrieve(url, tarball)  # noqa: S310 - URL comes from our own GitHub release asset
        extract_dir = Path(tmp) / "extracted"
        extract_dir.mkdir()
        with tarfile.open(tarball) as tf:
            tf.extractall(extract_dir)
        # The release tarball has one top-level folder (see .github/workflows/release.yml).
        release_root = next(p for p in extract_dir.iterdir() if p.is_dir())
        installer = release_root / "session" / "install.sh"
        subprocess.run(["bash", str(installer), "--from-release", str(release_root)], check=True, timeout=600)


async def apply_update(url: str | None) -> tuple[bool, str]:
    if not url:
        return False, "No update package available."
    try:
        await asyncio.to_thread(_download_extract_and_install, url)
        return True, "Updated — restarting."
    except Exception as exc:
        return False, f"Update failed: {exc}"
