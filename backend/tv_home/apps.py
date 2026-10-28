"""App list management: install/remove/move/launch and icon fetching.

Ported from v1's tv-home.py (install/remove/move/fetch_icon/norm_url/domain_of/
slugify) — this logic is already correct and tested against the real hardware;
only the storage/transport layer changed (atomic JSON file, now behind a FastAPI
route instead of http.server).
"""
import re
import time
import urllib.request
from pathlib import Path
from typing import Optional

from .config import APPS_FILE, CATALOG, ICONS
from .state_store import read_json, write_json


def load_apps() -> list[dict]:
    return read_json(APPS_FILE, [])


def save_apps(apps: list[dict]) -> None:
    write_json(APPS_FILE, apps)


def norm_url(url: str) -> str:
    url = url.strip().rstrip("/")
    m = re.match(r"^(https?://)([^/?#]+)(.*)$", url, re.I)
    return (m.group(1).lower() + m.group(2).lower() + m.group(3)) if m else url


def domain_of(url: str) -> str:
    return re.sub(r"^https?://", "", url, flags=re.I).split("/")[0].split("?")[0]


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or f"app{int(time.time())}"


def is_image(data: bytes) -> bool:
    return (
        data[:8] == b"\x89PNG\r\n\x1a\n"
        or data[:3] == b"\xff\xd8\xff"
        or (data[:4] == b"RIFF" and data[8:12] == b"WEBP")
    )


def fetch_icon(domain: str, out: Path) -> bool:
    for src in (
        f"https://{domain}/apple-touch-icon.png",
        f"https://www.google.com/s2/favicons?domain={domain}&sz=256",
    ):
        try:
            req = urllib.request.Request(src, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = r.read()
            if is_image(data):
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(data)
                return True
        except Exception:
            pass
    return False


def install(name: str, url: str, ua: Optional[str] = None, cid: Optional[str] = None) -> tuple[bool, str]:
    name = re.sub(r"[;=|<>]", "", name).strip()
    url = url.strip().replace(" ", "")
    if not name or not url:
        return False, "Enter both an app name and a website."
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    apps = load_apps()
    if any(norm_url(a["url"]) == norm_url(url) for a in apps):
        return False, f"{name} is already on your home screen."
    used = {a["id"] for a in apps}
    base = cid or "site-" + slugify(name)
    app_id, n = base, 2
    while app_id in used:
        app_id, n = f"{base}-{n}", n + 1
    fetch_icon(domain_of(url), ICONS / f"{app_id}.png")
    app = {"id": app_id, "name": name, "url": norm_url(url)}
    if ua:
        app["ua"] = ua
    apps.append(app)
    save_apps(apps)
    return True, f"{name} added to your home screen."


def remove(app_id: str) -> tuple[bool, str]:
    apps = load_apps()
    app = next((a for a in apps if a["id"] == app_id), None)
    if not app:
        return False, "That app isn't on your home screen."
    save_apps([a for a in apps if a["id"] != app_id])
    (ICONS / f"{app_id}.png").unlink(missing_ok=True)
    return True, f"{app['name']} removed from your home screen."


def move(app_id: str, direction: str) -> tuple[bool, str]:
    apps = load_apps()
    i = next((k for k, a in enumerate(apps) if a["id"] == app_id), None)
    j = None if i is None else i + (-1 if direction == "left" else 1)
    if i is None or j < 0 or j >= len(apps):
        return False, ""
    apps[i], apps[j] = apps[j], apps[i]
    save_apps(apps)
    return True, ""


def install_from_catalog(app_id: str) -> tuple[bool, str]:
    item = next((c for c in CATALOG if c["id"] == app_id), None)
    if not item:
        return False, "That app isn't in the catalog."
    return install(item["name"], item["url"], item.get("ua"), item["id"])


def catalog_view() -> list[dict]:
    installed = {norm_url(a["url"]) for a in load_apps()}
    return [
        {
            "id": c["id"],
            "name": c["name"],
            "cat": c["cat"],
            "domain": domain_of(c["url"]),
            "installed": norm_url(c["url"]) in installed,
        }
        for c in CATALOG
    ]


def apps_view() -> list[dict]:
    return [
        {"id": a["id"], "name": a["name"], "domain": domain_of(a["url"]), "icon": (ICONS / f"{a['id']}.png").exists()}
        for a in load_apps()
    ]
