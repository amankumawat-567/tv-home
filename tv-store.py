#!/usr/bin/env python3
"""TV App Store for Flex Launcher.

A full-screen, remote-friendly store for adding and removing streaming apps
on your Flex Launcher home screen.

  First time:  python3 tv-store.py setup
  Then:        open the "App Store" tile on your TV home screen
"""
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import threading
import time
import urllib.request
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOME = Path.home()
CONFIG = HOME / ".config/flex-launcher/config.ini"
ICONDIR = HOME / ".config/flex-launcher/assets/icons"
BIN = HOME / ".local/bin/tv-store"
PROFILE = HOME / ".config/tv-store/chrome-profile"
TV_UA = ("Mozilla/5.0 (Linux; Tizen 2.3; SmartHub; SMART-TV; SmartTV; U; Maple2012) "
         "AppleWebKit/538.1+ (KHTML, like Gecko) TV Safari/538.1+")

CATALOG = [
    {"id": "netflix", "name": "Netflix", "url": "https://www.netflix.com", "cat": "Movies & TV"},
    {"id": "jiohotstar", "name": "JioHotstar", "url": "https://www.hotstar.com/in", "cat": "Movies & TV"},
    {"id": "primevideo", "name": "Prime Video", "url": "https://www.primevideo.com", "cat": "Movies & TV"},
    {"id": "sonyliv", "name": "SonyLIV", "url": "https://www.sonyliv.com", "cat": "Movies & TV"},
    {"id": "zee5", "name": "ZEE5", "url": "https://www.zee5.com", "cat": "Movies & TV"},
    {"id": "appletv", "name": "Apple TV", "url": "https://tv.apple.com", "cat": "Movies & TV"},
    {"id": "crunchyroll", "name": "Crunchyroll", "url": "https://www.crunchyroll.com", "cat": "Anime"},
    {"id": "youtube", "name": "YouTube", "url": "https://www.youtube.com/tv", "cat": "Videos", "ua": TV_UA},
    {"id": "twitch", "name": "Twitch", "url": "https://www.twitch.tv", "cat": "Videos"},
    {"id": "spotify", "name": "Spotify", "url": "https://open.spotify.com", "cat": "Music"},
    {"id": "ytmusic", "name": "YouTube Music", "url": "https://music.youtube.com", "cat": "Music"},
    {"id": "jiosaavn", "name": "JioSaavn", "url": "https://www.jiosaavn.com", "cat": "Music"},
]

lock = threading.Lock()
changed = False
browser = None


# ---------------------------------------------------------------- config file

def norm_url(url):
    url = url.strip().rstrip("/")
    m = re.match(r"^(https?://)([^/?#]+)(.*)$", url, re.I)
    return (m.group(1).lower() + m.group(2).lower() + m.group(3)) if m else url


def domain_of(url):
    return re.sub(r"^https?://", "", url, flags=re.I).split("/")[0].split("?")[0]


def read_lines():
    return CONFIG.read_text(encoding="utf-8").splitlines()


def write_lines(lines):
    shutil.copy(CONFIG, CONFIG.with_suffix(".ini.bak"))
    tmp = CONFIG.with_suffix(".ini.tmp")
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.replace(tmp, CONFIG)


def section_bounds(lines, name):
    """Return (header_index, end_index) of a [section], or None."""
    start = None
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("["):
            if start is not None:
                return start, i
            if s == f"[{name}]":
                start = i
    return (start, len(lines)) if start is not None else None


def is_entry(line):
    s = line.strip()
    return bool(s) and s[0] not in "#;[" and "=" in s


def web_apps():
    """All website apps on the home screen: [{key, name, url}]."""
    lines = read_lines()
    bounds = section_bounds(lines, "Main")
    apps = []
    if not bounds:
        return apps
    for line in lines[bounds[0] + 1:bounds[1]]:
        if not is_entry(line) or "google-chrome --kiosk" not in line:
            continue
        key, value = line.strip().split("=", 1)
        parts = value.split(";", 2)
        if len(parts) < 3:
            continue
        m = re.search(r"(https?://\S+)\s*$", parts[2])
        if m:
            apps.append({"key": key, "name": parts[0], "url": norm_url(m.group(1))})
    return apps


def insert_entry(section, entry):
    lines = read_lines()
    bounds = section_bounds(lines, section)
    if not bounds:
        return False
    head, end = bounds
    last = submenu = None
    for i in range(head + 1, end):
        if is_entry(lines[i]):
            last = i
            if submenu is None and ":submenu" in lines[i]:
                submenu = i
    if submenu is not None:
        pos = submenu
    elif last is not None:
        pos = last + 1
    else:
        pos = head + 1
    lines.insert(pos, entry)
    write_lines(lines)
    return True


def remove_by_url(url):
    target = norm_url(url)
    lines = read_lines()
    bounds = section_bounds(lines, "Main")
    if not bounds:
        return False
    keep, removed = [], False
    for i, line in enumerate(lines):
        if (bounds[0] < i < bounds[1] and is_entry(line) and "google-chrome --kiosk" in line):
            m = re.search(r"(https?://\S+)\s*$", line)
            if m and norm_url(m.group(1)) == target:
                removed = True
                continue
        keep.append(line)
    if removed:
        write_lines(keep)
    return removed


# ---------------------------------------------------------------- icons

def is_image(data):
    return (data[:8] == b"\x89PNG\r\n\x1a\n" or data[:3] == b"\xff\xd8\xff"
            or (data[:4] == b"RIFF" and data[8:12] == b"WEBP"))


def fetch_icon(domain, out):
    for src in (f"https://{domain}/apple-touch-icon.png",
                f"https://www.google.com/s2/favicons?domain={domain}&sz=256"):
        try:
            req = urllib.request.Request(src, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = r.read()
            if is_image(data):
                out.write_bytes(data)
                return
        except Exception:
            pass
    fallback = ICONDIR / "system.png"
    if fallback.exists():
        shutil.copy(fallback, out)


def make_store_icon(out, size=256):
    """Draw a simple amber rounded square with a white plus, as a PNG."""
    radius, arm, thick = size * 0.22, size * 0.28, size * 0.09
    c = size / 2
    rows = []
    for y in range(size):
        row = bytearray([0])
        for x in range(size):
            dx = max(abs(x + 0.5 - c) - (c - radius), 0)
            dy = max(abs(y + 0.5 - c) - (c - radius), 0)
            inside = dx * dx + dy * dy <= radius * radius
            plus = ((abs(x + 0.5 - c) <= thick / 2 and abs(y + 0.5 - c) <= arm) or
                    (abs(y + 0.5 - c) <= thick / 2 and abs(x + 0.5 - c) <= arm))
            if not inside:
                row += bytes((0, 0, 0, 0))
            elif plus:
                row += bytes((255, 255, 255, 255))
            else:
                row += bytes((255, 181, 71, 255))
        rows.append(bytes(row))

    def chunk(kind, data):
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(b"".join(rows), 9))
           + chunk(b"IEND", b""))
    out.write_bytes(png)


# ---------------------------------------------------------------- actions

def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or f"app{int(time.time())}"


def install(name, url, ua=None):
    global changed
    name = re.sub(r"[;=|]", "", name).strip()
    url = url.strip().replace(" ", "").replace(";", "")
    if not name or not url:
        return False, "Enter both an app name and a website."
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    if any(a["url"] == norm_url(url) for a in web_apps()):
        return False, f"{name} is already on your home screen."
    if any(a["name"].lower() == name.lower() for a in web_apps()):
        return False, f"An app named {name} is already on your home screen."

    slug, used = slugify(name), {a["key"] for a in web_apps()}
    key, n = f"App_{slug}", 2
    while key in used:
        key, n = f"App_{slug}{n}", n + 1

    ICONDIR.mkdir(parents=True, exist_ok=True)
    icon = ICONDIR / f"{slug}.png"
    fetch_icon(domain_of(url), icon)
    flags = f'--user-agent="{ua}" ' if ua else ""
    if not insert_entry("Main", f"{key}={name};{icon};google-chrome --kiosk {flags}{url}"):
        return False, "Couldn't find the home screen menu in the launcher settings."
    changed = True
    return True, f"{name} added to your home screen."


def uninstall(url, name):
    global changed
    if remove_by_url(url):
        changed = True
        return True, f"{name} removed from your home screen."
    return False, f"{name} isn't on your home screen."


def state():
    installed = {a["url"]: a for a in web_apps()}
    catalog_urls = set()
    apps = []
    for item in CATALOG:
        u = norm_url(item["url"])
        catalog_urls.add(u)
        apps.append({"name": item["name"], "url": u, "cat": item["cat"],
                     "domain": domain_of(u), "installed": u in installed, "id": item["id"]})
    custom = [{"name": a["name"], "url": a["url"], "cat": "custom", "domain": domain_of(a["url"]),
               "installed": True, "id": "custom-" + a["key"]}
              for u, a in installed.items() if u not in catalog_urls]
    return {"apps": apps + custom}


# ---------------------------------------------------------------- web server

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send(self, body, ctype, code=200):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/":
            self.send(PAGE, "text/html; charset=utf-8")
        elif self.path == "/api/apps":
            with lock:
                self.send(json.dumps(state()), "application/json")
        else:
            self.send("Not found", "text/plain", 404)

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            data = {}
        with lock:
            if self.path == "/api/install":
                item = next((c for c in CATALOG if c["id"] == data.get("id")), None)
                if item:
                    ok, msg = install(item["name"], item["url"], item.get("ua"))
                else:
                    ok, msg = install(str(data.get("name", "")), str(data.get("url", "")))
            elif self.path == "/api/remove":
                ok, msg = uninstall(str(data.get("url", "")), str(data.get("name", "This app")))
            elif self.path == "/api/done":
                ok, msg = True, "Closing"
                threading.Timer(0.3, close_browser).start()
            else:
                self.send("Not found", "text/plain", 404)
                return
            body = state()
        body.update({"ok": ok, "message": msg})
        self.send(json.dumps(body), "application/json")


def close_browser():
    if browser and browser.poll() is None:
        browser.terminate()


def restart_launcher():
    if subprocess.run(["pgrep", "-x", "flex-launcher"], capture_output=True).returncode == 0:
        subprocess.run(["pkill", "-x", "flex-launcher"])
        time.sleep(1)
        subprocess.Popen(["flex-launcher"], start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def find_chrome():
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        path = shutil.which(name)
        if path:
            return path
    sys.exit("Google Chrome isn't installed. Install it first, then open the store again.")


def run_store():
    global browser
    if not CONFIG.exists():
        sys.exit(f"Flex Launcher settings not found at {CONFIG}")
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    PROFILE.mkdir(parents=True, exist_ok=True)
    browser = subprocess.Popen([
        find_chrome(), "--kiosk", f"--user-data-dir={PROFILE}", "--no-first-run",
        "--no-default-browser-check", "--disable-translate",
        f"http://127.0.0.1:{server.server_address[1]}/"])
    browser.wait()
    server.shutdown()
    if changed:
        restart_launcher()


def setup():
    if not CONFIG.exists():
        sys.exit(f"Flex Launcher settings not found at {CONFIG}. Set up Flex Launcher first.")
    BIN.parent.mkdir(parents=True, exist_ok=True)
    me = Path(__file__).resolve()
    if me != BIN.resolve():
        shutil.copy(me, BIN)
    BIN.chmod(0o755)
    ICONDIR.mkdir(parents=True, exist_ok=True)
    icon = ICONDIR / "app-store.png"
    make_store_icon(icon)
    if not any(l.strip().startswith("AppStore=") for l in read_lines()):
        if not insert_entry("Main", f"AppStore=App Store;{icon};{BIN}"):
            sys.exit("Couldn't find the [Main] menu in the launcher settings.")
    print("Done! The App Store tile is now on your TV home screen.")
    print("Restart the launcher (or the PC) to see it.")


# ---------------------------------------------------------------- page

PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>App Store</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Lexend:wght@400;500;700&display=swap" rel="stylesheet">
<style>
  :root {
    --night: #1c1838;
    --dusk: #2b2553;
    --dusk-high: #3a3270;
    --mist: #b8b1e0;
    --snow: #f5f2ff;
    --ember: #ffb547;
    --mint: #6fdcb8;
    color-scheme: dark;
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; height: 100%; }
  body {
    background: radial-gradient(120% 90% at 85% -10%, #4a2f6e 0%, var(--night) 55%) fixed;
    color: var(--snow);
    font: 400 18px/1.4 "Lexend", "Ubuntu", system-ui, sans-serif;
    overflow-y: auto;
  }
  header {
    display: flex; align-items: flex-end; justify-content: space-between; gap: 24px;
    padding: 40px 56px 8px;
  }
  h1 { margin: 0; font-weight: 700; font-size: 52px; letter-spacing: -0.02em; line-height: 1; }
  .sub { margin: 10px 0 0; color: var(--mist); font-size: 19px; }
  main { padding: 8px 56px 64px; }
  h2 { margin: 36px 0 16px; font-weight: 500; font-size: 24px; color: var(--mist); }
  .row { display: grid; grid-template-columns: repeat(auto-fill, minmax(176px, 1fr)); gap: 22px; }
  button { font: inherit; color: inherit; cursor: pointer; }
  .tile {
    position: relative; display: flex; flex-direction: column; align-items: center; gap: 14px;
    padding: 26px 14px 20px; border: 0; border-radius: 22px; background: var(--dusk);
    outline: 4px solid transparent; outline-offset: 0; scroll-margin: 48px;
    transition: transform .15s ease, outline-color .15s ease, background .15s ease, box-shadow .15s ease;
  }
  .tile:focus { outline-color: var(--ember); background: var(--dusk-high); transform: scale(1.06);
    box-shadow: 0 0 0 10px rgba(255, 181, 71, .14), 0 18px 40px rgba(0, 0, 0, .35); }
  .plate { width: 88px; height: 88px; border-radius: 22px; background: #fff; display: grid; place-items: center; overflow: hidden; }
  .plate img { width: 64px; height: 64px; object-fit: contain; }
  .plate.add { background: transparent; border: 3px dashed var(--mist); color: var(--mist); font-size: 52px; font-weight: 400; }
  .name { font-weight: 500; font-size: 19px; text-align: center; }
  .status { font-size: 15px; color: var(--mist); display: flex; align-items: center; gap: 7px; }
  .status.on { color: var(--mint); }
  .status.on::before { content: ""; width: 9px; height: 9px; border-radius: 50%; background: var(--mint); }
  .done {
    padding: 14px 34px; border: 0; border-radius: 999px; background: var(--snow); color: var(--night);
    font-weight: 700; font-size: 19px; outline: 4px solid transparent; outline-offset: 3px;
  }
  .done:focus { outline-color: var(--ember); }
  .hint { color: var(--mist); font-size: 15px; margin: 8px 0 0; text-align: right; }

  .scrim { position: fixed; inset: 0; background: rgba(12, 10, 28, .72); display: none; place-items: center; padding: 24px; }
  .scrim.open { display: grid; }
  .dialog { width: min(560px, 100%); background: var(--dusk); border-radius: 26px; padding: 34px; box-shadow: 0 30px 80px rgba(0,0,0,.5); }
  .dialog h3 { margin: 0 0 8px; font-size: 30px; font-weight: 700; }
  .dialog p { margin: 0 0 24px; color: var(--mist); }
  .dialog label { display: block; margin: 0 0 6px; font-weight: 500; }
  .dialog input {
    width: 100%; margin: 0 0 18px; padding: 14px 16px; border-radius: 14px; border: 2px solid var(--dusk-high);
    background: var(--night); color: var(--snow); font: inherit; outline: none;
  }
  .dialog input:focus { border-color: var(--ember); }
  .actions { display: flex; gap: 14px; flex-wrap: wrap; }
  .btn { padding: 14px 26px; border-radius: 999px; border: 0; font-weight: 700; outline: 4px solid transparent; outline-offset: 3px; }
  .btn:focus { outline-color: var(--ember); }
  .btn.primary { background: var(--ember); color: var(--night); }
  .btn.danger { background: #ff8a8a; color: var(--night); }
  .btn.quiet { background: var(--dusk-high); color: var(--snow); }
  .error { color: #ffb0b0; min-height: 1.4em; margin: -6px 0 14px; }

  .toast {
    position: fixed; left: 50%; bottom: 36px; transform: translate(-50%, 20px); opacity: 0;
    background: var(--snow); color: var(--night); font-weight: 500; padding: 14px 26px; border-radius: 999px;
    transition: opacity .2s ease, transform .2s ease; pointer-events: none;
  }
  .toast.show { opacity: 1; transform: translate(-50%, 0); }
  .busy .tile, .busy .btn { pointer-events: none; opacity: .7; }
  @media (prefers-reduced-motion: reduce) { * { transition: none !important; } .tile:focus { transform: none; } }
</style>
</head>
<body>
<header>
  <div>
    <h1>App Store</h1>
    <p class="sub">Pick the apps you want on your TV home screen.</p>
  </div>
  <div>
    <button class="done" data-nav id="done">Done</button>
    <p class="hint">Arrows to move, Enter to choose</p>
  </div>
</header>
<main id="main"></main>

<div class="scrim" id="scrim">
  <div class="dialog" role="dialog" aria-modal="true" id="dialog"></div>
</div>
<div class="toast" id="toast" role="status"></div>

<script>
const CATS = ["Movies & TV", "Anime", "Videos", "Music"];
let apps = [];
let lastFocus = null;

const $ = (s, el = document) => el.querySelector(s);
const esc = s => s.replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const icon = d => `https://www.google.com/s2/favicons?domain=${encodeURIComponent(d)}&sz=128`;

async function api(path, body) {
  const res = await fetch(path, body ? { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body) } : {});
  return res.json();
}

function tile(app) {
  return `<button class="tile" data-nav data-id="${esc(app.id)}">
    <span class="plate"><img src="${icon(app.domain)}" alt=""></span>
    <span class="name">${esc(app.name)}</span>
    <span class="status ${app.installed ? "on" : ""}">${app.installed ? "On home screen" : "Add"}</span>
  </button>`;
}

function render(keepId) {
  let html = "";
  for (const cat of CATS) {
    const list = apps.filter(a => a.cat === cat);
    if (list.length) html += `<h2>${cat}</h2><div class="row">${list.map(tile).join("")}</div>`;
  }
  const custom = apps.filter(a => a.cat === "custom");
  html += `<h2>Your own websites</h2><div class="row">${custom.map(tile).join("")}
    <button class="tile" data-nav id="add-site">
      <span class="plate add">+</span><span class="name">Add a website</span><span class="status">Any site you like</span>
    </button></div>`;
  $("#main").innerHTML = html;
  const target = keepId ? document.querySelector(`[data-id="${CSS.escape(keepId)}"]`) : null;
  (target || $(".tile")).focus();
}

function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => t.classList.remove("show"), 2600);
}

function openDialog(html) {
  lastFocus = document.activeElement;
  $("#dialog").innerHTML = html;
  $("#scrim").classList.add("open");
  ($("#dialog [data-first]") || $("#dialog [data-nav]")).focus();
}

function closeDialog() {
  $("#scrim").classList.remove("open");
  if (lastFocus && document.contains(lastFocus)) lastFocus.focus();
}

function dialogOpen() { return $("#scrim").classList.contains("open"); }

function askApp(app) {
  const verb = app.installed ? "Remove" : "Add";
  openDialog(`
    <h3>${esc(app.name)}</h3>
    <p>${app.installed ? "Remove this app from your home screen?" : "Add this app to your home screen?"}</p>
    <div class="actions">
      <button class="btn ${app.installed ? "danger" : "primary"}" data-nav data-first id="confirm">${verb}</button>
      <button class="btn quiet" data-nav id="cancel">Cancel</button>
    </div>`);
  $("#cancel").onclick = closeDialog;
  $("#confirm").onclick = async () => {
    document.body.classList.add("busy");
    const r = app.installed
      ? await api("/api/remove", { url: app.url, name: app.name })
      : await api("/api/install", app.cat === "custom" ? { name: app.name, url: app.url } : { id: app.id });
    document.body.classList.remove("busy");
    apps = r.apps;
    closeDialog();
    render(app.cat === "custom" && app.installed ? null : app.id);
    toast(r.message);
  };
}

function askWebsite() {
  openDialog(`
    <h3>Add a website</h3>
    <p>It opens full screen, like an app.</p>
    <label for="site-name">App name</label>
    <input id="site-name" data-nav data-first placeholder="e.g. Prime Video" autocomplete="off">
    <label for="site-url">Website</label>
    <input id="site-url" data-nav placeholder="e.g. primevideo.com" autocomplete="off" inputmode="url">
    <div class="error" id="site-error"></div>
    <div class="actions">
      <button class="btn primary" data-nav id="site-add">Add to home screen</button>
      <button class="btn quiet" data-nav id="cancel">Cancel</button>
    </div>`);
  $("#cancel").onclick = closeDialog;
  $("#site-add").onclick = async () => {
    const name = $("#site-name").value.trim(), url = $("#site-url").value.trim();
    if (!name || !url) { $("#site-error").textContent = "Enter both an app name and a website."; return; }
    document.body.classList.add("busy");
    const r = await api("/api/install", { name, url });
    document.body.classList.remove("busy");
    if (!r.ok) { $("#site-error").textContent = r.message; return; }
    apps = r.apps;
    closeDialog();
    render();
    toast(r.message);
  };
}

async function finish() {
  $("#main").innerHTML = `<h2>Updating your home screen…</h2>`;
  await api("/api/done", {});
}

document.addEventListener("click", e => {
  const t = e.target.closest(".tile");
  if (!t) return;
  if (t.id === "add-site") return askWebsite();
  const app = apps.find(a => a.id === t.dataset.id);
  if (app) askApp(app);
});
$("#done").onclick = finish;

function move(dir) {
  const scope = dialogOpen() ? $("#dialog") : document;
  const items = [...scope.querySelectorAll("[data-nav]")].filter(el => el.offsetParent !== null);
  const cur = document.activeElement;
  if (!items.includes(cur)) { items[0] && items[0].focus(); return; }
  const r = cur.getBoundingClientRect(), cx = r.left + r.width / 2, cy = r.top + r.height / 2;
  let best = null, bestScore = Infinity;
  for (const el of items) {
    if (el === cur) continue;
    const b = el.getBoundingClientRect();
    const dx = b.left + b.width / 2 - cx, dy = b.top + b.height / 2 - cy;
    let main, side;
    if (dir === "left")  { if (dx > -4) continue; main = -dx; side = Math.abs(dy); }
    if (dir === "right") { if (dx < 4)  continue; main = dx;  side = Math.abs(dy); }
    if (dir === "up")    { if (dy > -4) continue; main = -dy; side = Math.abs(dx); }
    if (dir === "down")  { if (dy < 4)  continue; main = dy;  side = Math.abs(dx); }
    const score = main + side * 2.5;
    if (score < bestScore) { bestScore = score; best = el; }
  }
  if (best) { best.focus(); best.scrollIntoView({ block: "nearest", inline: "nearest" }); }
}

document.addEventListener("keydown", e => {
  const typing = document.activeElement && document.activeElement.tagName === "INPUT";
  const dirs = { ArrowLeft: "left", ArrowRight: "right", ArrowUp: "up", ArrowDown: "down" };
  if (dirs[e.key]) {
    if (typing && (e.key === "ArrowLeft" || e.key === "ArrowRight")) return;
    e.preventDefault();
    move(dirs[e.key]);
  } else if (e.key === "Escape" || (e.key === "Backspace" && !typing)) {
    e.preventDefault();
    dialogOpen() ? closeDialog() : finish();
  } else if (e.key === "Enter" && typing) {
    e.preventDefault();
    $("#site-add") && $("#site-add").click();
  }
});

api("/api/apps").then(r => { apps = r.apps; render(); });
</script>
</body>
</html>
"""


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        setup()
    else:
        run_store()
