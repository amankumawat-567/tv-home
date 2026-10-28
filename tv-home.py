#!/usr/bin/env python3
"""TV Home: an Android TV-style home screen for your Linux PC.

Wide app banners over a wallpaper, a clock, a built-in App Store and a
settings menu, all usable with arrow keys and Enter (or a phone remote).

  First time:  python3 tv-home.py setup
  Then:        restart the PC, or run  tv-home
"""
import json
import os
import pwd
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOME = Path.home()
APPDIR = HOME / ".config/tv-home"
APPS_FILE = APPDIR / "apps.json"
SETTINGS_FILE = APPDIR / "settings.json"
ICONS = APPDIR / "icons"
PROFILE = APPDIR / "chrome-profile"
USER_WALLS = APPDIR / "wallpapers"
BIN = HOME / ".local/bin/tv-home"
FLEX_CONFIG = HOME / ".config/flex-launcher/config.ini"
PORT = 47800
WALL_DIRS = [USER_WALLS, Path("/usr/share/xfce4/backdrops"), Path("/usr/share/backgrounds")]

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
browser = None


# ---------------------------------------------------------------- storage

def read_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def load_apps():
    return read_json(APPS_FILE, [])


def save_apps(apps):
    write_json(APPS_FILE, apps)


def norm_url(url):
    url = url.strip().rstrip("/")
    m = re.match(r"^(https?://)([^/?#]+)(.*)$", url, re.I)
    return (m.group(1).lower() + m.group(2).lower() + m.group(3)) if m else url


def domain_of(url):
    return re.sub(r"^https?://", "", url, flags=re.I).split("/")[0].split("?")[0]


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or f"app{int(time.time())}"


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
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(data)
                return True
        except Exception:
            pass
    return False


# ---------------------------------------------------------------- actions

def install(name, url, ua=None, cid=None):
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


def remove(app_id):
    apps = load_apps()
    app = next((a for a in apps if a["id"] == app_id), None)
    if not app:
        return False, "That app isn't on your home screen."
    save_apps([a for a in apps if a["id"] != app_id])
    (ICONS / f"{app_id}.png").unlink(missing_ok=True)
    return True, f"{app['name']} removed from your home screen."


def move(app_id, direction):
    apps = load_apps()
    i = next((k for k, a in enumerate(apps) if a["id"] == app_id), None)
    j = None if i is None else i + (-1 if direction == "left" else 1)
    if i is None or j < 0 or j >= len(apps):
        return False, ""
    apps[i], apps[j] = apps[j], apps[i]
    save_apps(apps)
    return True, ""


def find_chrome():
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        path = shutil.which(name)
        if path:
            return path
    return None


def launch(app_id):
    app = next((a for a in load_apps() if a["id"] == app_id), None)
    chrome = find_chrome()
    if not app:
        return False, "That app isn't on your home screen."
    if not chrome:
        return False, "Google Chrome isn't installed."
    cmd = [chrome, "--kiosk", "--password-store=basic"]
    if app.get("ua"):
        cmd.append(f"--user-agent={app['ua']}")
    cmd.append(app["url"])
    subprocess.Popen(cmd, start_new_session=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return True, f"Opening {app['name']}"


def wallpapers():
    found = []
    for d in WALL_DIRS:
        if not d.is_dir():
            continue
        for p in sorted(d.rglob("*")):
            if (p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp") and p.is_file()
                    and p.stat().st_size > 100_000 and len(p.relative_to(d).parts) <= 3):
                found.append(p)
    return found


def current_wallpaper():
    walls = wallpapers()
    if not walls:
        return None
    idx = read_json(SETTINGS_FILE, {}).get("wallpaper", 0)
    return walls[idx % len(walls)]


def system(action):
    if action == "wallpaper":
        settings = read_json(SETTINGS_FILE, {})
        settings["wallpaper"] = settings.get("wallpaper", 0) + 1
        write_json(SETTINGS_FILE, settings)
        return True, "Wallpaper changed."
    if action == "desktop":
        threading.Timer(0.3, close_browser).start()
        return True, "Going to the desktop"
    commands = {"poweroff": ["systemctl", "poweroff"], "reboot": ["systemctl", "reboot"],
                "suspend": ["systemctl", "suspend"]}
    if action in commands:
        subprocess.Popen(commands[action], start_new_session=True)
        return True, ""
    return False, "Unknown action."


# ---------------------------------------------------------------- go home (close apps)

def go_home():
    """Close every app window (Chrome kiosk windows that aren't the home screen).

    Chrome rewrites its own process title, so the command line is matched as one
    string, and the program is identified from /proc/<pid>/exe.
    """
    closed = 0
    for pid in os.listdir("/proc"):
        if not pid.isdigit() or int(pid) == os.getpid():
            continue
        try:
            exe = os.path.basename(os.readlink(f"/proc/{pid}/exe"))
            cmd = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode(errors="ignore")
        except Exception:
            continue
        if exe not in ("chrome", "chromium", "chromium-browser"):
            continue
        if "--kiosk" not in cmd or "--type=" in cmd or str(PROFILE) in cmd:
            continue
        try:
            os.kill(int(pid), signal.SIGTERM)
            closed += 1
        except Exception:
            pass
    return True, "" if closed else "No app is open."


# ---------------------------------------------------------------- settings helpers

def run_cmd(args, timeout=20):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except FileNotFoundError:
        return 127, "", f"{args[0]} is not installed."
    except subprocess.TimeoutExpired:
        return 124, "", "That took too long. Try again."


def ip_address():
    code, out, _ = run_cmd(["hostname", "-I"], 5)
    return out.split()[0] if code == 0 and out.split() else ""


def split_nm(line):
    """Split an `nmcli -t` line, honouring escaped colons."""
    parts, cur, escaped = [], "", False
    for ch in line:
        if escaped:
            cur += ch
            escaped = False
        elif ch == "\\":
            escaped = True
        elif ch == ":":
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    return parts


def nm_error(text):
    t = text.strip()
    if "Secrets were required" in t or "psk" in t.lower() or "password" in t.lower():
        return "Wrong or missing password."
    if "not authorized" in t.lower():
        return "This change needs permission. Try it from the desktop."
    if "No network with SSID" in t:
        return "That network is out of range."
    return re.sub(r"^Error:\s*", "", t.splitlines()[-1] if t else "Something went wrong.")


def net_state(rescan=False):
    code, out, err = run_cmd(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device"])
    if code:
        return {"available": False, "error": "Network settings aren't available on this PC."}
    devices = [split_nm(l) for l in out.splitlines() if l.strip()]
    wifi_dev = next((d for d in devices if len(d) > 3 and d[1] == "wifi"), None)
    eth = next((d for d in devices if len(d) > 3 and d[1] == "ethernet" and d[2].startswith("connected")), None)
    radio = run_cmd(["nmcli", "radio", "wifi"])[1].strip() == "enabled"
    saved = {split_nm(l)[0] for l in run_cmd(["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show"])[1].splitlines()
             if l.strip() and "wireless" in l}
    networks = {}
    if wifi_dev and radio:
        _, out, _ = run_cmd(["nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY", "device", "wifi", "list",
                             "--rescan", "yes" if rescan else "auto"], 40)
        for line in out.splitlines():
            p = split_nm(line)
            if len(p) < 4 or not p[1]:
                continue
            n = {"ssid": p[1], "signal": int(p[2]) if p[2].isdigit() else 0,
                 "secure": p[3] not in ("", "--"), "active": p[0] == "*", "saved": p[1] in saved}
            old = networks.get(p[1])
            if not old or (not old["active"] and (n["active"] or n["signal"] > old["signal"])):
                networks[p[1]] = n
    ordered = sorted(networks.values(), key=lambda n: (not n["active"], not n["saved"], -n["signal"]))
    return {"available": True, "wifi": bool(wifi_dev), "device": wifi_dev[0] if wifi_dev else "",
            "wifiOn": radio, "ethernet": bool(eth), "networks": ordered[:20], "ip": ip_address()}


def net_action(data):
    act, ssid = data.get("action"), str(data.get("ssid", ""))
    if act == "radio":
        code, out, err = run_cmd(["nmcli", "radio", "wifi", "on" if data.get("on") else "off"])
        return code == 0, "" if code == 0 else nm_error(err or out)
    if act == "connect":
        if data.get("saved"):
            args = ["nmcli", "connection", "up", "id", ssid]
        else:
            args = ["nmcli", "device", "wifi", "connect", ssid]
            if data.get("password"):
                args += ["password", str(data["password"])]
        code, out, err = run_cmd(args, 60)
        return code == 0, f"Connected to {ssid}." if code == 0 else nm_error(err or out)
    if act == "disconnect":
        dev = net_state().get("device", "")
        code, out, err = run_cmd(["nmcli", "device", "disconnect", dev])
        return code == 0, f"Disconnected from {ssid}." if code == 0 else nm_error(err or out)
    if act == "forget":
        code, out, err = run_cmd(["nmcli", "connection", "delete", "id", ssid])
        return code == 0, f"Forgot {ssid}." if code == 0 else nm_error(err or out)
    return False, "Unknown action."


MAC_RE = re.compile(r"^[0-9A-F]{2}(:[0-9A-F]{2}){5}$", re.I)


def bt_state(scan=False):
    code, out, err = run_cmd(["bluetoothctl", "show"], 10)
    if code == 127:
        return {"available": False, "error": "Bluetooth tools aren't installed."}
    if code or "Controller" not in out:
        return {"available": False, "error": "This PC has no Bluetooth adapter. Plug in a USB Bluetooth adapter to use Bluetooth."}
    powered = "Powered: yes" in out
    if scan and powered:
        run_cmd(["bluetoothctl", "--timeout", "10", "scan", "on"], 20)
    devices = []
    for line in run_cmd(["bluetoothctl", "devices"])[1].splitlines():
        m = re.match(r"^Device\s+(\S+)\s+(.*)$", line.strip())
        if not m or not MAC_RE.match(m.group(1)):
            continue
        mac, name = m.group(1), m.group(2).strip()
        info = run_cmd(["bluetoothctl", "info", mac], 8)[1]
        paired = "Paired: yes" in info
        if not paired and (not name or re.fullmatch(r"([0-9A-F]{2}-){5}[0-9A-F]{2}", name, re.I)):
            continue
        devices.append({"mac": mac, "name": name, "paired": paired, "connected": "Connected: yes" in info})
        if len(devices) >= 25:
            break
    devices.sort(key=lambda d: (not d["connected"], not d["paired"], d["name"].lower()))
    return {"available": True, "powered": powered, "devices": devices}


def bt_action(data):
    act, mac = data.get("action"), str(data.get("mac", ""))
    if act == "power":
        if data.get("on"):
            run_cmd(["rfkill", "unblock", "bluetooth"], 5)
        code, out, err = run_cmd(["bluetoothctl", "power", "on" if data.get("on") else "off"])
        ok = code == 0 and "Failed" not in out
        return ok, "" if ok else "Couldn't change Bluetooth power."
    if not MAC_RE.match(mac):
        return False, "Unknown device."
    name = str(data.get("name", "Device"))
    if act == "connect":
        if "Paired: yes" not in run_cmd(["bluetoothctl", "info", mac], 8)[1]:
            code, out, err = run_cmd(["bluetoothctl", "--agent", "NoInputNoOutput", "pair", mac], 40)
            if code or "Failed" in out:
                return False, f"Couldn't pair with {name}. Put it in pairing mode and try again."
        run_cmd(["bluetoothctl", "trust", mac])
        code, out, err = run_cmd(["bluetoothctl", "connect", mac], 40)
        ok = code == 0 and "Failed" not in out
        return ok, f"{name} connected." if ok else f"Couldn't connect to {name}. Make sure it's on and nearby."
    if act == "disconnect":
        code, out, _ = run_cmd(["bluetoothctl", "disconnect", mac], 20)
        return code == 0, f"{name} disconnected."
    if act == "forget":
        code, out, _ = run_cmd(["bluetoothctl", "remove", mac], 20)
        return code == 0, f"Forgot {name}."
    return False, "Unknown action."


SINK = "@DEFAULT_AUDIO_SINK@"


def sound_state():
    code, out, err = run_cmd(["wpctl", "get-volume", SINK])
    m = re.search(r"Volume:\s*([\d.]+)", out)
    if code or not m:
        return {"available": False, "error": "Sound settings aren't available on this PC."}
    outputs, in_audio, in_sinks = [], False, False
    for raw in run_cmd(["wpctl", "status"])[1].splitlines():
        if raw.strip() == "Audio":
            in_audio = True
            continue
        if in_audio and raw.strip() in ("Video", "Settings"):
            break
        line = raw.strip(" │├└─\t")
        if not in_audio:
            continue
        if line.startswith("Sinks:"):
            in_sinks = True
            continue
        if in_sinks:
            sm = re.match(r"^(\*\s+)?(\d+)\.\s+(.*?)\s*(\[vol:[^\]]*\])?\s*$", line)
            if not sm:
                in_sinks = False
                continue
            outputs.append({"id": sm.group(2), "name": sm.group(3), "current": bool(sm.group(1))})
    return {"available": True, "volume": round(float(m.group(1)) * 100), "muted": "MUTED" in out,
            "outputs": outputs}


def sound_action(data):
    act = data.get("action")
    if act == "up":
        run_cmd(["wpctl", "set-volume", "-l", "1.0", SINK, "5%+"])
    elif act == "down":
        run_cmd(["wpctl", "set-volume", SINK, "5%-"])
    elif act == "mute":
        run_cmd(["wpctl", "set-mute", SINK, "toggle"])
    elif act == "output" and str(data.get("id", "")).isdigit():
        run_cmd(["wpctl", "set-default", str(data["id"])])
    else:
        return False, "Unknown action."
    return True, ""


def about():
    info = {}
    try:
        info["system"] = re.search(r'PRETTY_NAME="([^"]+)"', Path("/etc/os-release").read_text()).group(1)
    except Exception:
        info["system"] = "Linux"
    try:
        info["processor"] = re.search(r"model name\s*:\s*(.+)", Path("/proc/cpuinfo").read_text()).group(1).strip()
    except Exception:
        info["processor"] = ""
    try:
        mem = dict(re.findall(r"^(\w+):\s+(\d+)", Path("/proc/meminfo").read_text(), re.M))
        total, avail = int(mem["MemTotal"]) / 1048576, int(mem["MemAvailable"]) / 1048576
        info["memory"] = f"{total - avail:.1f} GB used of {total:.1f} GB"
    except Exception:
        info["memory"] = ""
    du = shutil.disk_usage("/")
    info["storage"] = f"{du.free / 1e9:.0f} GB free of {du.total / 1e9:.0f} GB"
    info["ip"] = ip_address() or "Not connected"
    return info


def display_name():
    try:
        gecos = pwd.getpwuid(os.getuid()).pw_gecos.split(",")[0].strip()
        if gecos:
            return gecos.split()[0]
    except Exception:
        pass
    return os.environ.get("USER", "").capitalize()


def state():
    apps = load_apps()
    installed = {norm_url(a["url"]) for a in apps}
    return {
        "user": display_name(),
        "wallpaper": current_wallpaper() is not None,
        "apps": [{"id": a["id"], "name": a["name"], "domain": domain_of(a["url"]),
                  "icon": (ICONS / f"{a['id']}.png").exists()} for a in apps],
        "catalog": [{"id": c["id"], "name": c["name"], "cat": c["cat"], "domain": domain_of(c["url"]),
                     "installed": norm_url(c["url"]) in installed} for c in CATALOG],
    }


# ---------------------------------------------------------------- import from Flex Launcher

def migrate_from_flex():
    """Bring over website apps already on the Flex Launcher home screen."""
    if APPS_FILE.exists() or not FLEX_CONFIG.exists():
        return
    apps, in_main = [], False
    for line in FLEX_CONFIG.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("["):
            in_main = s == "[Main]"
            continue
        if not in_main or "google-chrome --kiosk" not in s or "=" not in s:
            continue
        value = s.split("=", 1)[1]
        parts = value.split(";", 2)
        m = re.search(r"(https?://\S+)\s*$", s)
        if len(parts) < 3 or not m:
            continue
        url = norm_url(m.group(1))
        item = next((c for c in CATALOG if norm_url(c["url"]) == url), None)
        app_id = item["id"] if item else "site-" + slugify(parts[0])
        if any(a["id"] == app_id for a in apps):
            continue
        app = {"id": app_id, "name": item["name"] if item else parts[0], "url": url}
        if item and item.get("ua"):
            app["ua"] = item["ua"]
        apps.append(app)
        old_icon = Path(parts[1])
        ICONS.mkdir(parents=True, exist_ok=True)
        if not fetch_icon(domain_of(url), ICONS / f"{app_id}.png") and old_icon.exists():
            shutil.copy(old_icon, ICONS / f"{app_id}.png")
    save_apps(apps)


# ---------------------------------------------------------------- web server

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send(self, data, ctype, code=200):
        if isinstance(data, str):
            data = data.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/":
            self.send(PAGE, "text/html; charset=utf-8")
        elif path == "/api/state":
            with lock:
                self.send(json.dumps(state()), "application/json")
        elif path.startswith("/icons/"):
            name = path[len("/icons/"):]
            icon = ICONS / name
            if re.fullmatch(r"[a-z0-9-]+\.png", name) and icon.exists():
                self.send(icon.read_bytes(), "image/png")
            else:
                self.send("Not found", "text/plain", 404)
        elif path in ("/api/net", "/api/bt", "/api/sound", "/api/about"):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            flag = q.get("scan", ["0"])[0] == "1"
            data = {"/api/net": lambda: net_state(flag), "/api/bt": lambda: bt_state(flag),
                    "/api/sound": sound_state, "/api/about": about}[path]()
            self.send(json.dumps(data), "application/json")
        elif path == "/wallpaper":
            wall = current_wallpaper()
            if wall:
                types = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
                self.send(wall.read_bytes(), types.get(wall.suffix.lower(), "image/jpeg"))
            else:
                self.send("Not found", "text/plain", 404)
        else:
            self.send("Not found", "text/plain", 404)

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            data = {}
        path = self.path
        quick = {"/api/home": lambda: go_home(), "/api/net": lambda: net_action(data),
                 "/api/bt": lambda: bt_action(data), "/api/sound": lambda: sound_action(data)}
        if path in quick:
            ok, msg = quick[path]()
            self.send(json.dumps({"ok": ok, "message": msg}), "application/json")
            return
        with lock:
            if path == "/api/install":
                item = next((c for c in CATALOG if c["id"] == data.get("id")), None)
                if item:
                    ok, msg = install(item["name"], item["url"], item.get("ua"), item["id"])
                else:
                    ok, msg = install(str(data.get("name", "")), str(data.get("url", "")))
            elif path == "/api/remove":
                ok, msg = remove(str(data.get("id", "")))
            elif path == "/api/move":
                ok, msg = move(str(data.get("id", "")), str(data.get("dir", "")))
            elif path == "/api/launch":
                ok, msg = launch(str(data.get("id", "")))
            elif path == "/api/system":
                ok, msg = system(str(data.get("action", "")))
            else:
                self.send("Not found", "text/plain", 404)
                return
            body = state()
        body.update({"ok": ok, "message": msg})
        self.send(json.dumps(body), "application/json")


def close_browser():
    if browser and browser.poll() is None:
        browser.terminate()


def run():
    global browser
    try:
        server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    except OSError:
        sys.exit("TV Home is already running.")
    threading.Thread(target=server.serve_forever, daemon=True).start()
    migrate_from_flex()
    chrome = find_chrome()
    if not chrome:
        sys.exit("Google Chrome isn't installed. Install it first, then start TV Home again.")
    PROFILE.mkdir(parents=True, exist_ok=True)
    browser = subprocess.Popen([
        chrome, "--kiosk", "--password-store=basic", f"--user-data-dir={PROFILE}", "--no-first-run",
        "--no-default-browser-check", "--disable-translate", "--disable-extensions",
        "--disable-background-networking", "--disable-features=Translate",
        f"http://127.0.0.1:{PORT}/"])
    browser.wait()
    server.shutdown()


HOME_CMD = f"wget -q -O /dev/null --post-data= http://127.0.0.1:{PORT}/api/home"
SESSION_FILE = Path("/usr/share/xsessions/tv-home.desktop")


def write_key_files():
    home_keys = (f'"{HOME_CMD}"\n    F12\n\n'
                 f'"{HOME_CMD}"\n    XF86HomePage\n\n')
    volume_keys = (f'"wpctl set-volume -l 1.0 {SINK} 5%+"\n    XF86AudioRaiseVolume\n\n'
                   f'"wpctl set-volume {SINK} 5%-"\n    XF86AudioLowerVolume\n\n'
                   f'"wpctl set-mute {SINK} toggle"\n    XF86AudioMute\n')
    escape_key = (f'"pkill -f {PROFILE}"\n    Control+Alt + d\n\n')
    (APPDIR / "keys-tv.rc").write_text(home_keys + escape_key + volume_keys, encoding="utf-8")
    (APPDIR / "keys-desktop.rc").write_text(home_keys, encoding="utf-8")


def write_session_script():
    script = HOME / ".local/bin/tv-session"
    script.write_text(f"""#!/bin/sh
# TV-only session: straight into TV Home. If TV Home closes or fails,
# the normal Xubuntu desktop starts instead, so you never get stuck on a black screen.
xset s off -dpms
command -v xfsettingsd >/dev/null && xfsettingsd &
xfwm4 &
for agent in /usr/libexec/polkit-mate-authentication-agent-1 \\
             /usr/lib/x86_64-linux-gnu/polkit-mate/polkit-mate-authentication-agent-1 \\
             /usr/libexec/xfce-polkit \\
             /usr/lib/x86_64-linux-gnu/polkit-gnome/polkit-gnome-authentication-agent-1; do
  [ -x "$agent" ] && {{ "$agent" & break; }}
done
command -v xbindkeys >/dev/null && xbindkeys -f "{APPDIR}/keys-tv.rc"
[ -x /usr/lib/x86_64-linux-gnu/libexec/kdeconnectd ] && /usr/lib/x86_64-linux-gnu/libexec/kdeconnectd &
sleep 1
"{BIN}"
# TV Home has closed: switch to the full desktop in the same session.
pkill -x xbindkeys; pkill -x xfwm4; pkill -x xfsettingsd; pkill -f polkit-.*-authentication-agent
exec startxfce4
""", encoding="utf-8")
    script.chmod(0o755)


def setup():
    BIN.parent.mkdir(parents=True, exist_ok=True)
    me = Path(__file__).resolve()
    if me != BIN.resolve():
        shutil.copy(me, BIN)
    BIN.chmod(0o755)
    APPDIR.mkdir(parents=True, exist_ok=True)
    USER_WALLS.mkdir(parents=True, exist_ok=True)
    migrate_from_flex()

    if not shutil.which("xbindkeys"):
        print("Installing xbindkeys (for the Home key)...")
        subprocess.run(["sudo", "apt", "install", "-y", "xbindkeys"])
    write_key_files()
    write_session_script()

    entry = ("[Desktop Entry]\nType=Application\nName=TV Home\n"
             "Comment=Android TV-style home screen\n"
             f"Exec={BIN}\nIcon=video-display\nTerminal=false\nCategories=AudioVideo;\n")
    menu = HOME / ".local/share/applications"
    menu.mkdir(parents=True, exist_ok=True)
    (menu / "tv-home.desktop").write_text(entry, encoding="utf-8")

    autostart = HOME / ".config/autostart"
    autostart.mkdir(parents=True, exist_ok=True)
    (autostart / "tv-home-keys.desktop").write_text(
        "[Desktop Entry]\nType=Application\nName=TV Home keys\n"
        f"Exec=xbindkeys -f {APPDIR}/keys-desktop.rc\nTerminal=false\n", encoding="utf-8")
    if SESSION_FILE.exists():
        (autostart / "tv.desktop").unlink(missing_ok=True)
        mode = "TV-only mode (boots straight into TV Home)"
    else:
        (autostart / "tv.desktop").write_text(entry, encoding="utf-8")
        mode = "desktop mode (starts after the desktop loads)"

    print(f"Done! TV Home is set up with {len(load_apps())} app(s), in {mode}.")
    print("Press F12 (or the Home button on a remote) to close an app and go home.")
    print("In TV-only mode, Ctrl+Alt+D always gets you to the normal desktop.")
    print("Restart the PC to apply everything.")


# ---------------------------------------------------------------- page

PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TV Home</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Lexend:wght@300;400;500;700&display=swap" rel="stylesheet">
<style>
  :root {
    --night: #15122b;
    --dusk: #2b2553;
    --dusk-high: #3a3270;
    --mist: #c9c3ec;
    --snow: #f7f5ff;
    --ember: #ffb547;
    --mint: #6fdcb8;
    color-scheme: dark;
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; height: 100%; overflow: hidden; }
  body { background: var(--night); color: var(--snow); font: 400 18px/1.4 "Lexend", "Ubuntu", system-ui, sans-serif; }
  button { font: inherit; color: inherit; cursor: pointer; border: 0; background: none; padding: 0; }
  button:focus { outline: none; }

  /* ---------- home ---------- */
  #wall { position: fixed; inset: 0; background: center / cover no-repeat;
          background-image: radial-gradient(90% 70% at 75% 10%, #5a3c8a 0%, transparent 60%),
                            linear-gradient(160deg, #2a1f55 0%, #15122b 70%); }
  .shade { position: fixed; inset: 0; pointer-events: none;
           background: linear-gradient(180deg, rgba(10,8,24,.55) 0%, rgba(10,8,24,0) 26%,
                                                rgba(10,8,24,0) 42%, rgba(10,8,24,.78) 70%, rgba(10,8,24,.94) 100%); }
  .top { position: fixed; top: 0; left: 0; right: 0; display: flex; justify-content: space-between;
         align-items: flex-start; padding: 38px 64px 0; }
  #greet { font-size: 30px; font-weight: 500; letter-spacing: -0.01em; text-shadow: 0 2px 12px rgba(0,0,0,.4); }
  #date { color: var(--mist); font-size: 18px; margin-top: 2px; text-shadow: 0 2px 10px rgba(0,0,0,.4); }
  .right { display: flex; align-items: center; gap: 22px; }
  #clock { font-size: 54px; font-weight: 300; letter-spacing: -0.02em; line-height: 1; text-shadow: 0 2px 16px rgba(0,0,0,.4); }
  #clock small { font-size: 20px; font-weight: 400; margin-left: 6px; color: var(--mist); }
  .gear { width: 54px; height: 54px; border-radius: 50%; display: grid; place-items: center;
          background: rgba(255,255,255,.12); transition: transform .15s ease, background .15s ease, box-shadow .15s ease; }
  .gear svg { width: 28px; height: 28px; fill: var(--snow); }
  .gear:focus { background: var(--snow); transform: scale(1.12); box-shadow: 0 10px 30px rgba(0,0,0,.45); }
  .gear:focus svg { fill: var(--night); }

  .dock { position: fixed; left: 0; right: 0; bottom: 0; padding: 0 0 54px; }
  .dock h2 { margin: 0 0 6px 64px; font-size: 20px; font-weight: 500; color: var(--mist); }
  .rail { overflow-x: auto; overflow-y: hidden; scrollbar-width: none; padding: 26px 64px 46px; }
  .rail::-webkit-scrollbar { display: none; }
  .track { display: flex; align-items: center; gap: 22px; width: max-content; }

  .apps-btn { width: 126px; display: flex; flex-direction: column; align-items: center; gap: 10px; flex: none; }
  .apps-btn .disc { width: 92px; height: 92px; border-radius: 50%; background: var(--ember); display: grid;
                    grid-template-columns: repeat(3, 10px); gap: 7px; place-content: center;
                    transition: transform .15s ease, box-shadow .15s ease; }
  .apps-btn .disc i { width: 10px; height: 10px; border-radius: 3px; background: var(--night); }
  .apps-btn span { font-size: 17px; color: var(--mist); }
  .apps-btn:focus .disc { transform: scale(1.12); box-shadow: 0 0 0 4px var(--snow), 0 14px 34px rgba(0,0,0,.5); }
  .apps-btn:focus span { color: var(--snow); }

  .banner { position: relative; flex: none; width: 224px; height: 126px; border-radius: 10px;
            background: var(--bg, #ffffff); display: grid; place-items: center; scroll-margin: 0 120px;
            box-shadow: 0 6px 18px rgba(0,0,0,.35);
            transition: transform .16s ease, box-shadow .16s ease; }
  .banner img { width: 78px; height: 78px; object-fit: contain; border-radius: 14px; }
  .banner .word { font-size: 24px; font-weight: 700; color: var(--fg, #15122b); padding: 0 14px; text-align: center; }
  .banner .cap { position: absolute; top: calc(100% + 12px); left: 0; right: 0; text-align: center;
                 font-size: 17px; font-weight: 500; opacity: 0; transition: opacity .15s ease; white-space: nowrap; }
  .banner:focus { transform: scale(1.12); z-index: 2;
                  box-shadow: 0 0 0 3px var(--snow), 0 22px 44px rgba(0,0,0,.6); }
  .banner:focus .cap { opacity: 1; }
  .banner.first { width: 300px; }
  .empty { width: 330px; height: 126px; border-radius: 10px; border: 3px dashed var(--mist); color: var(--mist);
           display: grid; place-items: center; font-weight: 500; flex: none; }
  .empty:focus { border-color: var(--snow); color: var(--snow); transform: scale(1.06); }

  #launch { position: fixed; inset: 0; background: rgba(10,8,24,.88); display: none; place-items: center; text-align: center; }
  #launch.open { display: grid; }
  #launch .badge { width: 110px; height: 110px; border-radius: 24px; margin: 0 auto 22px; display: grid; place-items: center; background: var(--bg, #fff); }
  #launch .badge img { width: 72px; height: 72px; object-fit: contain; border-radius: 14px; }
  #launch p { margin: 0; font-size: 26px; font-weight: 500; }
  #launch .launch-hint { margin-top: 12px; font-size: 18px; font-weight: 400; color: var(--mist); }

  /* ---------- store ---------- */
  #store { position: fixed; inset: 0; overflow-y: auto; display: none;
           background: radial-gradient(120% 90% at 85% -10%, #4a2f6e 0%, var(--night) 55%); }
  #store.open { display: block; }
  .s-head { display: flex; align-items: flex-end; justify-content: space-between; gap: 24px; padding: 40px 56px 8px; }
  .s-head h1 { margin: 0; font-weight: 700; font-size: 50px; letter-spacing: -0.02em; line-height: 1; }
  .s-head p { margin: 10px 0 0; color: var(--mist); font-size: 19px; }
  .s-body { padding: 8px 56px 64px; }
  .s-body h2 { margin: 34px 0 16px; font-weight: 500; font-size: 23px; color: var(--mist); }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(176px, 1fr)); gap: 22px; }
  .tile { display: flex; flex-direction: column; align-items: center; gap: 14px; padding: 26px 14px 20px;
          border-radius: 22px; background: var(--dusk); scroll-margin: 48px;
          transition: transform .15s ease, background .15s ease, box-shadow .15s ease; }
  .tile:focus { background: var(--dusk-high); transform: scale(1.06);
                box-shadow: 0 0 0 4px var(--ember), 0 0 0 14px rgba(255,181,71,.14), 0 18px 40px rgba(0,0,0,.35); }
  .plate { width: 88px; height: 88px; border-radius: 22px; background: #fff; display: grid; place-items: center; overflow: hidden; }
  .plate img { width: 64px; height: 64px; object-fit: contain; }
  .plate.add { background: transparent; border: 3px dashed var(--mist); color: var(--mist); font-size: 52px; }
  .name { font-weight: 500; font-size: 19px; text-align: center; }
  .status { font-size: 15px; color: var(--mist); display: flex; align-items: center; gap: 7px; }
  .status.on { color: var(--mint); }
  .status.on::before { content: ""; width: 9px; height: 9px; border-radius: 50%; background: var(--mint); }


  /* ---------- settings ---------- */
  #settings { position: fixed; inset: 0; display: none; overflow: hidden;
              background: radial-gradient(120% 90% at 85% -10%, #4a2f6e 0%, var(--night) 55%); }
  #settings.open { display: grid; grid-template-columns: 290px 1fr; grid-template-rows: auto 1fr; }
  #settings .s-head { grid-column: 1 / -1; }
  .set-nav { display: flex; flex-direction: column; gap: 8px; padding: 28px 0 40px 56px; }
  .nav-item { text-align: left; padding: 14px 20px; border-radius: 14px; font-size: 19px; color: var(--mist);
              transition: background .12s ease, color .12s ease; }
  .nav-item.current { background: var(--dusk); color: var(--snow); }
  .nav-item:focus { background: var(--snow); color: var(--night); }
  .set-panel { overflow-y: auto; padding: 28px 56px 48px 36px; }
  .set-panel h2 { margin: 0 0 6px; font-size: 30px; font-weight: 700; color: var(--snow); }
  .set-panel .lead { margin: 0 0 22px; color: var(--mist); font-size: 18px; }
  .set-panel .actions { margin-bottom: 24px; }
  .set-panel h3 { margin: 26px 0 12px; font-size: 19px; font-weight: 500; color: var(--mist); }
  .rowbtn { display: flex; justify-content: space-between; align-items: center; gap: 20px; width: 100%;
            padding: 16px 22px; margin-bottom: 10px; border-radius: 16px; background: var(--dusk);
            text-align: left; scroll-margin: 24px; transition: background .12s ease, box-shadow .12s ease; }
  .rowbtn:focus { background: var(--dusk-high); box-shadow: 0 0 0 4px var(--ember); }
  .rowbtn .meta { color: var(--mist); font-size: 16px; white-space: nowrap; }
  .rowbtn .meta.on { color: var(--mint); }
  .vol { display: flex; align-items: center; gap: 22px; margin: 4px 0 26px; }
  .vol .num { font-size: 64px; font-weight: 300; min-width: 150px; }
  .vol .bar { flex: 1; max-width: 420px; height: 10px; border-radius: 99px; background: var(--dusk-high); overflow: hidden; }
  .vol .bar i { display: block; height: 100%; background: var(--ember); }
  .vol.muted .num, .vol.muted .bar i { opacity: .4; }
  .facts { display: grid; grid-template-columns: 180px 1fr; gap: 14px 24px; margin: 0; font-size: 18px; }
  .facts dt { color: var(--mist); }
  .facts dd { margin: 0; }
  .keys { margin-top: 30px; padding: 18px 22px; border-radius: 16px; background: var(--dusk); color: var(--mist); }
  .keys b { color: var(--snow); font-weight: 500; }
  .loading { color: var(--mist); }

  /* ---------- shared ---------- */
  .pill { padding: 14px 30px; border-radius: 999px; font-weight: 700; background: var(--snow); color: var(--night);
          transition: transform .12s ease, box-shadow .12s ease; }
  .pill:focus { box-shadow: 0 0 0 4px var(--ember); transform: scale(1.05); }
  .pill.quiet { background: var(--dusk-high); color: var(--snow); }
  .pill.primary { background: var(--ember); color: var(--night); }
  .pill.danger { background: #ff8a8a; color: var(--night); }

  .scrim { position: fixed; inset: 0; background: rgba(10,8,24,.74); display: none; place-items: center; padding: 24px; }
  .scrim.open { display: grid; }
  .dialog { width: min(620px, 100%); background: var(--dusk); border-radius: 26px; padding: 34px; box-shadow: 0 30px 80px rgba(0,0,0,.5); }
  .dialog h3 { margin: 0 0 8px; font-size: 30px; font-weight: 700; }
  .dialog p { margin: 0 0 24px; color: var(--mist); }
  .dialog label { display: block; margin: 0 0 6px; font-weight: 500; }
  .dialog input { width: 100%; margin: 0 0 18px; padding: 14px 16px; border-radius: 14px; border: 2px solid var(--dusk-high);
                  background: var(--night); color: var(--snow); font: inherit; outline: none; }
  .dialog input:focus { border-color: var(--ember); }
  .actions { display: flex; gap: 14px; flex-wrap: wrap; }
  .error { color: #ffb0b0; min-height: 1.4em; margin: -6px 0 14px; }
  .toast { position: fixed; left: 50%; top: 36px; transform: translate(-50%, -16px); opacity: 0; z-index: 9;
           background: var(--snow); color: var(--night); font-weight: 500; padding: 14px 26px; border-radius: 999px;
           transition: opacity .2s ease, transform .2s ease; pointer-events: none; }
  .toast.show { opacity: 1; transform: translate(-50%, 0); }
  .busy button { pointer-events: none; opacity: .7; }
  @media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
</style>
</head>
<body>
<div id="wall"></div>
<div class="shade"></div>

<header class="top">
  <div>
    <div id="greet">Hello</div>
    <div id="date"></div>
  </div>
  <div class="right">
    <div id="clock"></div>
    <button class="gear" data-nav id="gear" aria-label="Settings">
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19.4 13a7.6 7.6 0 0 0 0-2l2.1-1.6-2-3.5-2.5 1a7.4 7.4 0 0 0-1.7-1L15 3.3h-4l-.4 2.6a7.4 7.4 0 0 0-1.7 1l-2.5-1-2 3.5L6.6 11a7.6 7.6 0 0 0 0 2l-2.1 1.6 2 3.5 2.5-1a7.4 7.4 0 0 0 1.7 1l.4 2.6h4l.4-2.6a7.4 7.4 0 0 0 1.7-1l2.5 1 2-3.5zM13 15.5a3.5 3.5 0 1 1 0-7 3.5 3.5 0 0 1 0 7z" transform="translate(-1 0)"/></svg>
    </button>
  </div>
</header>

<section class="dock">
  <h2>Your apps</h2>
  <div class="rail" id="rail"><div class="track" id="track"></div></div>
</section>

<div id="launch"><div><div class="badge" id="launch-badge"></div><p id="launch-text"></p><p class="launch-hint">Press F12 or Home on your remote to come back here</p></div></div>

<section id="store">
  <div class="s-head">
    <div><h1>App Store</h1><p>Pick the apps you want on your home screen.</p></div>
    <button class="pill" data-nav id="store-back">Back to home</button>
  </div>
  <div class="s-body" id="store-body"></div>
</section>

<section id="settings">
  <div class="s-head">
    <div><h1>Settings</h1><p>Network, sound, Bluetooth and more.</p></div>
    <button class="pill" data-nav id="settings-back">Back to home</button>
  </div>
  <nav class="set-nav" id="set-nav"></nav>
  <div class="set-panel" id="set-panel"></div>
</section>

<div class="scrim" id="scrim"><div class="dialog" role="dialog" aria-modal="true" id="dialog"></div></div>
<div class="toast" id="toast" role="status"></div>

<script>
const CATS = ["Movies & TV", "Anime", "Videos", "Music"];
let S = { apps: [], catalog: [], user: "", wallpaper: false };
let lastFocus = null, launching = false, holdTimer = null, wallVersion = 0;
const colors = {};

const $ = (s, el = document) => el.querySelector(s);
const esc = s => String(s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const favicon = d => `https://www.google.com/s2/favicons?domain=${encodeURIComponent(d)}&sz=128`;
const iconUrl = a => a.icon ? `/icons/${a.id}.png` : favicon(a.domain);
const storeOpen = () => $("#store").classList.contains("open");
const dialogOpen = () => $("#scrim").classList.contains("open");

async function api(path, body) {
  const res = await fetch(path, body ? { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body) } : {});
  return res.json();
}

/* ---------- clock & greeting ---------- */
function tick() {
  const now = new Date();
  const parts = now.toLocaleTimeString([], { hour: "numeric", minute: "2-digit", hour12: true }).split(" ");
  $("#clock").innerHTML = `${esc(parts[0])}<small>${esc((parts[1] || "").toLowerCase())}</small>`;
  $("#date").textContent = now.toLocaleDateString([], { weekday: "long", day: "numeric", month: "long" });
  const h = now.getHours();
  const part = h < 5 ? "Good night" : h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
  $("#greet").textContent = S.user ? `${part}, ${S.user}` : part;
}

/* ---------- banner colour from the app's own icon ---------- */
function bannerColor(img) {
  try {
    const c = document.createElement("canvas"); c.width = c.height = 32;
    const x = c.getContext("2d"); x.drawImage(img, 0, 0, 32, 32);
    const d = x.getImageData(0, 0, 32, 32).data;
    const edge = [], all = [];
    for (let y = 0; y < 32; y++) for (let k = 0; k < 32; k++) {
      const i = (y * 32 + k) * 4; if (d[i + 3] < 200) continue;
      const px = [d[i], d[i + 1], d[i + 2]];
      all.push(px); if (y < 2 || y > 29 || k < 2 || k > 29) edge.push(px);
    }
    if (!all.length) return null;
    const mean = list => [0, 1, 2].map(j => Math.round(list.reduce((s, p) => s + p[j], 0) / list.length));
    const lum = c => (0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]) / 255;
    if (edge.length > 150) {                       // icon fills its square: extend its own background
      const c = mean(edge);
      return { bg: `rgb(${c})`, fg: lum(c) > 0.6 ? "#15122b" : "#ffffff" };
    }
    // logo on a transparent background: use a plain banner that contrasts with it
    return lum(mean(all)) > 0.8 ? { bg: "#1d1b26", fg: "#ffffff" } : { bg: "#ffffff", fg: "#15122b" };
  } catch (e) { return null; }
}

function paint(el, id) {
  const c = colors[id]; if (!c) return;
  el.style.setProperty("--bg", c.bg); el.style.setProperty("--fg", c.fg);
}

/* ---------- home ---------- */
function renderHome(focusId) {
  let html = `<button class="apps-btn" data-nav id="open-store"><span class="disc">${"<i></i>".repeat(9)}</span><span>Apps</span></button>`;
  if (!S.apps.length) {
    html += `<button class="empty" data-nav id="empty-add">Add your first app</button>`;
  }
  S.apps.forEach((a, i) => {
    html += `<button class="banner" data-nav data-id="${esc(a.id)}">
      <img src="${iconUrl(a)}" alt="" data-for="${esc(a.id)}">
      <span class="cap">${esc(a.name)}</span></button>`;
  });
  $("#track").innerHTML = html;
  $("#track").querySelectorAll("img[data-for]").forEach(img => {
    const id = img.dataset.for, el = img.closest(".banner");
    if (colors[id]) { paint(el, id); return; }
    img.addEventListener("load", () => { const c = bannerColor(img); if (c) { colors[id] = c; paint(el, id); } });
    img.addEventListener("error", () => {
      const a = S.apps.find(x => x.id === id);
      img.replaceWith(Object.assign(document.createElement("span"), { className: "word", textContent: a ? a.name : "" }));
    });
  });
  const target = focusId && document.querySelector(`.banner[data-id="${CSS.escape(focusId)}"]`);
  (target || $(".banner") || $("#open-store")).focus();
}

function setWallpaper() {
  if (!S.wallpaper) return;
  const url = `/wallpaper?v=${wallVersion}`;
  const probe = new Image();
  probe.onload = () => { $("#wall").style.backgroundImage = `url("${url}")`; };
  probe.src = url;
}

async function openApp(id) {
  if (launching) return;
  const a = S.apps.find(x => x.id === id); if (!a) return;
  launching = true;
  const c = colors[id] || { bg: "#fff" };
  $("#launch-badge").style.setProperty("--bg", c.bg);
  $("#launch-badge").innerHTML = `<img src="${iconUrl(a)}" alt="">`;
  $("#launch-text").textContent = `Opening ${a.name}`;
  $("#launch").classList.add("open");
  const r = await api("/api/launch", { id });
  if (!r.ok) { endLaunch(); toast(r.message); return; }
  setTimeout(endLaunch, 12000);
}
function endLaunch() { launching = false; $("#launch").classList.remove("open"); }
window.addEventListener("focus", () => { if (launching) setTimeout(endLaunch, 400); });

/* ---------- store ---------- */
function storeTile(c) {
  return `<button class="tile" data-nav data-cid="${esc(c.id)}">
    <span class="plate"><img src="${favicon(c.domain)}" alt=""></span>
    <span class="name">${esc(c.name)}</span>
    <span class="status ${c.installed ? "on" : ""}">${c.installed ? "On home screen" : "Add"}</span></button>`;
}
function siteTile(a) {
  return `<button class="tile" data-nav data-site="${esc(a.id)}">
    <span class="plate"><img src="${iconUrl(a)}" alt=""></span>
    <span class="name">${esc(a.name)}</span>
    <span class="status on">On home screen</span></button>`;
}
function renderStore(focusSel) {
  let html = "";
  for (const cat of CATS) {
    const list = S.catalog.filter(c => c.cat === cat);
    if (list.length) html += `<h2>${cat}</h2><div class="grid">${list.map(storeTile).join("")}</div>`;
  }
  const own = S.apps.filter(a => a.id.startsWith("site-"));
  html += `<h2>Your own websites</h2><div class="grid">${own.map(siteTile).join("")}
    <button class="tile" data-nav id="add-site"><span class="plate add">+</span>
    <span class="name">Add a website</span><span class="status">Any site you like</span></button></div>`;
  $("#store-body").innerHTML = html;
  (focusSel && $(focusSel) || $("#store .tile")).focus();
}
function openStore() { $("#store").classList.add("open"); renderStore(); }
function closeStore() { $("#store").classList.remove("open"); renderHome(); $("#open-store").focus(); }

/* ---------- dialogs ---------- */
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
function toast(msg) {
  if (!msg) return;
  const t = $("#toast"); t.textContent = msg; t.classList.add("show");
  clearTimeout(toast.t); toast.t = setTimeout(() => t.classList.remove("show"), 2600);
}
async function busy(fn) {
  document.body.classList.add("busy");
  try { return await fn(); } finally { document.body.classList.remove("busy"); }
}

function askCatalog(c) {
  openDialog(`<h3>${esc(c.name)}</h3>
    <p>${c.installed ? "Remove this app from your home screen?" : "Add this app to your home screen?"}</p>
    <div class="actions">
      <button class="pill ${c.installed ? "danger" : "primary"}" data-nav data-first id="ok">${c.installed ? "Remove" : "Add"}</button>
      <button class="pill quiet" data-nav id="cancel">Cancel</button></div>`);
  $("#cancel").onclick = closeDialog;
  $("#ok").onclick = () => busy(async () => {
    const r = c.installed ? await api("/api/remove", { id: c.id }) : await api("/api/install", { id: c.id });
    S = r; closeDialog(); renderStore(`[data-cid="${c.id}"]`); toast(r.message);
  });
}
function askSite(a) {
  openDialog(`<h3>${esc(a.name)}</h3><p>Remove this website from your home screen?</p>
    <div class="actions"><button class="pill danger" data-nav data-first id="ok">Remove</button>
    <button class="pill quiet" data-nav id="cancel">Cancel</button></div>`);
  $("#cancel").onclick = closeDialog;
  $("#ok").onclick = () => busy(async () => {
    const r = await api("/api/remove", { id: a.id }); S = r; closeDialog(); renderStore("#add-site"); toast(r.message);
  });
}
function askWebsite() {
  openDialog(`<h3>Add a website</h3><p>It opens full screen, like an app.</p>
    <label for="site-name">App name</label>
    <input id="site-name" data-nav data-first placeholder="e.g. Hoichoi" autocomplete="off">
    <label for="site-url">Website</label>
    <input id="site-url" data-nav placeholder="e.g. hoichoi.tv" autocomplete="off" inputmode="url">
    <div class="error" id="site-error"></div>
    <div class="actions"><button class="pill primary" data-nav id="site-add">Add to home screen</button>
    <button class="pill quiet" data-nav id="cancel">Cancel</button></div>`);
  $("#cancel").onclick = closeDialog;
  $("#site-add").onclick = () => {
    const name = $("#site-name").value.trim(), url = $("#site-url").value.trim();
    if (!name || !url) { $("#site-error").textContent = "Enter both an app name and a website."; return; }
    busy(async () => {
      const r = await api("/api/install", { name, url });
      if (!r.ok) { $("#site-error").textContent = r.message; return; }
      S = r; closeDialog(); renderStore("#add-site"); toast(r.message);
    });
  };
}
function appOptions(id) {
  const a = S.apps.find(x => x.id === id); if (!a) return;
  const i = S.apps.indexOf(a);
  openDialog(`<h3>${esc(a.name)}</h3><p>Rearrange or remove this app.</p>
    <div class="actions">
      ${i > 0 ? `<button class="pill quiet" data-nav data-first id="mv-left">Move left</button>` : ""}
      ${i < S.apps.length - 1 ? `<button class="pill quiet" data-nav ${i === 0 ? "data-first" : ""} id="mv-right">Move right</button>` : ""}
      <button class="pill danger" data-nav id="rm">Remove</button>
      <button class="pill quiet" data-nav id="cancel">Cancel</button></div>`);
  $("#cancel").onclick = closeDialog;
  const mv = dir => busy(async () => { S = await api("/api/move", { id, dir }); closeDialog(); renderHome(id); });
  if ($("#mv-left")) $("#mv-left").onclick = () => mv("left");
  if ($("#mv-right")) $("#mv-right").onclick = () => mv("right");
  $("#rm").onclick = () => busy(async () => { const r = await api("/api/remove", { id }); S = r; closeDialog(); renderHome(); toast(r.message); });
}
/* ---------- settings ---------- */
const SECTIONS = [["network", "Wi-Fi & network"], ["bluetooth", "Bluetooth"], ["sound", "Sound"],
                  ["wallpaper", "Wallpaper"], ["power", "Power"], ["about", "About"]];
let section = "network", NET = null, BT = null, SND = null;
const settingsOpen = () => $("#settings").classList.contains("open");

function openSettings() {
  $("#settings").classList.add("open");
  $("#set-nav").innerHTML = SECTIONS.map(([id, label]) =>
    `<button class="nav-item" data-nav data-sec="${id}">${label}</button>`).join("");
  showSection("network");
  $(`.nav-item[data-sec="network"]`).focus();
}
function closeSettings() { $("#settings").classList.remove("open"); $("#gear").focus(); }
function setPanel(html, refocus) {
  $("#set-panel").innerHTML = html;
  if (refocus) { const el = $(`#set-panel ${refocus}`); if (el) el.focus(); }
}
function showSection(id, refocus) {
  section = id;
  document.querySelectorAll(".nav-item").forEach(b => b.classList.toggle("current", b.dataset.sec === id));
  ({ network: renderNetwork, bluetooth: renderBluetooth, sound: renderSound,
     wallpaper: renderWallpaper, power: renderPower, about: renderAbout })[id](refocus);
}
const strength = s => s >= 70 ? "Strong" : s >= 40 ? "Good" : "Weak";

async function renderNetwork(refocus, rescan) {
  setPanel(`<h2>Wi-Fi & network</h2><p class="lead loading">${rescan ? "Searching for networks…" : "Checking your connection…"}</p>`);
  const s = NET = await api(`/api/net${rescan ? "?scan=1" : ""}`);
  if (section !== "network") return;
  if (!s.available) return setPanel(`<h2>Wi-Fi & network</h2><p class="lead">${esc(s.error)}</p>`);
  const active = s.networks.find(n => n.active);
  const status = active ? `Connected to ${esc(active.ssid)}` : s.ethernet ? "Connected with a network cable" : "Not connected";
  let html = `<h2>Wi-Fi & network</h2><p class="lead">${status}${s.ip ? `. IP address ${esc(s.ip)}` : ""}</p>`;
  if (!s.wifi) {
    html += `<p class="lead">This PC has no Wi-Fi adapter. Plug in a USB Wi-Fi adapter to use Wi-Fi.</p>`;
  } else {
    html += `<div class="actions">
      <button class="pill quiet" data-nav data-act="wifi-power">${s.wifiOn ? "Turn Wi-Fi off" : "Turn Wi-Fi on"}</button>
      ${s.wifiOn ? `<button class="pill quiet" data-nav data-act="wifi-scan">Search again</button>` : ""}</div>`;
    if (s.wifiOn) {
      html += s.networks.length ? s.networks.map((n, i) => {
        const meta = [n.active ? "Connected" : n.saved ? "Saved" : "", n.secure ? "Secured" : "Open", strength(n.signal)].filter(Boolean).join(", ");
        return `<button class="rowbtn" data-nav data-act="wifi-pick" data-i="${i}"><span>${esc(n.ssid)}</span>
                <span class="meta ${n.active ? "on" : ""}">${meta}</span></button>`;
      }).join("") : `<p class="lead">No networks found. Choose Search again.</p>`;
    }
  }
  setPanel(html, refocus);
}

function wifiDialog(n) {
  const btn = (act, label, cls = "quiet", first = false) =>
    `<button class="pill ${cls}" data-nav ${first ? "data-first" : ""} data-wact="${act}">${label}</button>`;
  let body, buttons;
  if (n.active) { body = "You're connected to this network."; buttons = btn("disconnect", "Disconnect", "quiet", true) + btn("forget", "Forget", "danger"); }
  else if (n.saved) { body = "This network is saved on this PC."; buttons = btn("connect", "Connect", "primary", true) + btn("forget", "Forget", "danger"); }
  else if (n.secure) { body = `<label for="wifi-pass">Password</label><input id="wifi-pass" type="password" data-nav data-first autocomplete="off">`; buttons = btn("connect", "Connect", "primary"); }
  else { body = "This is an open network."; buttons = btn("connect", "Connect", "primary", true); }
  openDialog(`<h3>${esc(n.ssid)}</h3>${n.secure && !n.saved && !n.active ? body : `<p>${body}</p>`}
    <div class="error" id="wifi-error"></div>
    <div class="actions">${buttons}<button class="pill quiet" data-nav id="cancel">Cancel</button></div>`);
  $("#cancel").onclick = closeDialog;
  $("#dialog").querySelectorAll("[data-wact]").forEach(b => b.onclick = () => busy(async () => {
    const action = b.dataset.wact, password = $("#wifi-pass") ? $("#wifi-pass").value : "";
    if (action === "connect" && n.secure && !n.saved && !password) { $("#wifi-error").textContent = "Enter the Wi-Fi password."; return; }
    if (action === "connect") $("#wifi-error").textContent = "Connecting…";
    const r = await api("/api/net", { action, ssid: n.ssid, password, saved: n.saved });
    if (!r.ok) { $("#wifi-error").textContent = r.message; return; }
    closeDialog(); toast(r.message); renderNetwork(".rowbtn");
  }));
}

async function renderBluetooth(refocus, scan) {
  setPanel(`<h2>Bluetooth</h2><p class="lead loading">${scan ? "Searching for devices for about 10 seconds…" : "Checking Bluetooth…"}</p>`);
  const s = BT = await api(`/api/bt${scan ? "?scan=1" : ""}`);
  if (section !== "bluetooth") return;
  if (!s.available) return setPanel(`<h2>Bluetooth</h2><p class="lead">${esc(s.error)}</p>`);
  let html = `<h2>Bluetooth</h2><p class="lead">${s.powered ? "Put your device in pairing mode, then choose Search for devices." : "Bluetooth is off."}</p>
    <div class="actions"><button class="pill quiet" data-nav data-act="bt-power">${s.powered ? "Turn Bluetooth off" : "Turn Bluetooth on"}</button>
    ${s.powered ? `<button class="pill quiet" data-nav data-act="bt-scan">Search for devices</button>` : ""}</div>`;
  if (s.powered) {
    const row = (d, i) => `<button class="rowbtn" data-nav data-act="bt-pick" data-i="${i}"><span>${esc(d.name)}</span>
      <span class="meta ${d.connected ? "on" : ""}">${d.connected ? "Connected" : d.paired ? "Paired" : "Available"}</span></button>`;
    const paired = s.devices.map((d, i) => [d, i]).filter(([d]) => d.paired);
    const found = s.devices.map((d, i) => [d, i]).filter(([d]) => !d.paired);
    if (paired.length) html += `<h3>Your devices</h3>` + paired.map(([d, i]) => row(d, i)).join("");
    if (found.length) html += `<h3>Available devices</h3>` + found.map(([d, i]) => row(d, i)).join("");
    if (!s.devices.length) html += `<p class="lead">No devices yet.</p>`;
  }
  setPanel(html, refocus);
}

function btDialog(d) {
  const b = (act, label, cls = "quiet", first = false) =>
    `<button class="pill ${cls}" data-nav ${first ? "data-first" : ""} data-bact="${act}">${label}</button>`;
  const buttons = d.connected ? b("disconnect", "Disconnect", "quiet", true) + b("forget", "Forget", "danger")
                : d.paired ? b("connect", "Connect", "primary", true) + b("forget", "Forget", "danger")
                : b("connect", "Pair and connect", "primary", true);
  openDialog(`<h3>${esc(d.name)}</h3><p>${d.paired ? "This device is paired with this PC." : "Make sure the device is in pairing mode."}</p>
    <div class="error" id="bt-error"></div>
    <div class="actions">${buttons}<button class="pill quiet" data-nav id="cancel">Cancel</button></div>`);
  $("#cancel").onclick = closeDialog;
  $("#dialog").querySelectorAll("[data-bact]").forEach(btn => btn.onclick = () => busy(async () => {
    if (btn.dataset.bact === "connect") $("#bt-error").textContent = "Connecting… this can take up to 30 seconds.";
    const r = await api("/api/bt", { action: btn.dataset.bact, mac: d.mac, name: d.name });
    if (!r.ok) { $("#bt-error").textContent = r.message; return; }
    closeDialog(); toast(r.message); renderBluetooth(".rowbtn");
  }));
}

async function renderSound(refocus) {
  const s = SND = await api("/api/sound");
  if (section !== "sound") return;
  if (!s.available) return setPanel(`<h2>Sound</h2><p class="lead">${esc(s.error)}</p>`, refocus);
  let html = `<h2>Sound</h2><p class="lead">${s.muted ? "Sound is muted." : "Volume for everything on this TV."}</p>
    <div class="vol ${s.muted ? "muted" : ""}"><span class="num">${s.volume}%</span><span class="bar"><i style="width:${Math.min(s.volume, 100)}%"></i></span></div>
    <div class="actions">
      <button class="pill quiet" data-nav data-act="vol-down">Volume down</button>
      <button class="pill quiet" data-nav data-act="vol-up">Volume up</button>
      <button class="pill quiet" data-nav data-act="vol-mute">${s.muted ? "Unmute" : "Mute"}</button></div>`;
  if (s.outputs.length > 1) {
    html += `<h3>Play sound through</h3>` + s.outputs.map(o =>
      `<button class="rowbtn" data-nav data-act="vol-out" data-id="${esc(o.id)}"><span>${esc(o.name)}</span>
       <span class="meta ${o.current ? "on" : ""}">${o.current ? "In use" : ""}</span></button>`).join("");
  }
  setPanel(html, refocus);
}

function renderWallpaper(refocus) {
  setPanel(`<h2>Wallpaper</h2>
    <p class="lead">${S.wallpaper ? "Switch to the next picture." : "No pictures found yet."} To use your own photos, copy them into the wallpapers folder in TV Home's settings folder (~/.config/tv-home/wallpapers).</p>
    <div class="actions"><button class="pill primary" data-nav data-act="wall-next">Next wallpaper</button></div>`, refocus);
}

function renderPower(refocus) {
  setPanel(`<h2>Power</h2><p class="lead">Choose what to do with this TV.</p>
    <div class="actions">
      <button class="pill quiet" data-nav data-act="sys-suspend">Sleep</button>
      <button class="pill quiet" data-nav data-act="sys-reboot">Restart</button>
      <button class="pill danger" data-nav data-act="sys-poweroff">Shut down</button>
      <button class="pill quiet" data-nav data-act="sys-desktop">Go to desktop</button></div>`, refocus);
}

async function renderAbout(refocus) {
  const a = await api("/api/about");
  if (section !== "about") return;
  setPanel(`<h2>About this TV</h2><p class="lead">How your PC is doing.</p>
    <dl class="facts">
      <dt>System</dt><dd>${esc(a.system)}</dd>
      <dt>Processor</dt><dd>${esc(a.processor)}</dd>
      <dt>Memory</dt><dd>${esc(a.memory)}</dd>
      <dt>Storage</dt><dd>${esc(a.storage)}</dd>
      <dt>IP address</dt><dd>${esc(a.ip)}</dd>
    </dl>
    <div class="keys"><b>To leave an app</b>, press F12 or the Home button on your remote.<br>
      <b>To move or remove an app</b>, hold Enter on its banner.</div>`, refocus);
}

async function settingsAction(btn) {
  const act = btn.dataset.act, keep = `[data-act="${act}"]`;
  if (act === "wifi-scan") return renderNetwork(keep, true);
  if (act === "wifi-power") { await api("/api/net", { action: "radio", on: !NET.wifiOn }); return renderNetwork(keep); }
  if (act === "wifi-pick") return wifiDialog(NET.networks[+btn.dataset.i]);
  if (act === "bt-scan") return renderBluetooth(keep, true);
  if (act === "bt-power") {
    const r = await api("/api/bt", { action: "power", on: !BT.powered }); if (!r.ok) toast(r.message);
    return renderBluetooth(keep);
  }
  if (act === "bt-pick") return btDialog(BT.devices[+btn.dataset.i]);
  if (act.startsWith("vol-")) {
    const action = { "vol-up": "up", "vol-down": "down", "vol-mute": "mute", "vol-out": "output" }[act];
    await api("/api/sound", { action, id: btn.dataset.id });
    return renderSound(act === "vol-out" ? `[data-id="${btn.dataset.id}"]` : keep);
  }
  if (act === "wall-next") {
    const r = await api("/api/system", { action: "wallpaper" }); S = { ...S, ...r };
    if (!S.wallpaper) return toast("Add pictures to the wallpapers folder first.");
    wallVersion++; setWallpaper(); return toast("Wallpaper changed.");
  }
  if (act.startsWith("sys-")) {
    const action = act.slice(4);
    const labels = { suspend: "Sleep", reboot: "Restart", poweroff: "Shut down", desktop: "Go to desktop" };
    openDialog(`<h3>${labels[action]}?</h3><p>${action === "desktop" ? "TV Home will close and the normal desktop will open." : "Any open app will close."}</p>
      <div class="actions"><button class="pill ${action === "poweroff" ? "danger" : "primary"}" data-nav data-first id="ok">${labels[action]}</button>
      <button class="pill quiet" data-nav id="cancel">Cancel</button></div>`);
    $("#cancel").onclick = closeDialog;
    $("#ok").onclick = async () => { closeDialog(); await api("/api/system", { action }); };
  }
}

/* ---------- input ---------- */
document.addEventListener("click", e => {
  const t = e.target.closest("button"); if (!t) return;
  if (t.id === "open-store" || t.id === "empty-add") return openStore();
  if (t.id === "store-back") return closeStore();
  if (t.id === "gear") return openSettings();
  if (t.id === "settings-back") return closeSettings();
  if (t.dataset.sec) return showSection(t.dataset.sec, `[data-nav]`);
  if (t.dataset.act && t.closest("#set-panel")) return settingsAction(t);
  if (t.id === "add-site") return askWebsite();
  if (t.dataset.cid) return askCatalog(S.catalog.find(c => c.id === t.dataset.cid));
  if (t.dataset.site) return askSite(S.apps.find(a => a.id === t.dataset.site));
  if (t.classList.contains("banner") && e.detail !== 0) return openApp(t.dataset.id);
});
document.addEventListener("contextmenu", e => {
  const b = e.target.closest(".banner"); if (!b) return;
  e.preventDefault(); appOptions(b.dataset.id);
});

function move(dir) {
  const scope = dialogOpen() ? $("#dialog") : storeOpen() ? $("#store") : settingsOpen() ? $("#settings") : document.body;
  const items = [...scope.querySelectorAll("[data-nav]")].filter(el => el.offsetParent !== null &&
    (scope !== document.body || !el.closest("#store, #scrim, #settings")));
  const cur = document.activeElement;
  if (!items.includes(cur)) { items[0] && items[0].focus(); return; }
  const r = cur.getBoundingClientRect(), cx = r.left + r.width / 2, cy = r.top + r.height / 2;
  let best = null, bestScore = Infinity;
  for (const el of items) {
    if (el === cur) continue;
    const b = el.getBoundingClientRect();
    const hGap = Math.max(0, b.left - r.right, r.left - b.right);
    const vGap = Math.max(0, b.top - r.bottom, r.top - b.bottom);
    const bx = b.left + b.width / 2, by = b.top + b.height / 2;
    let main, side;
    if (dir === "left")  { if (b.right > r.left + 4) continue; main = r.left - b.right; side = vGap; }
    if (dir === "right") { if (b.left < r.right - 4) continue; main = b.left - r.right; side = vGap; }
    if (dir === "up")    { if (b.bottom > r.top + 4) continue; main = r.top - b.bottom; side = hGap; }
    if (dir === "down")  { if (b.top < r.bottom - 4) continue; main = b.top - r.bottom; side = hGap; }
    const align = (dir === "left" || dir === "right") ? Math.abs(by - cy) : Math.abs(bx - cx);
    const score = Math.max(main, 0) + side * 3 + align * 0.05;
    if (score < bestScore) { bestScore = score; best = el; }
  }
  if (best && dir === "left" && cur.closest("#set-panel") && best.classList.contains("nav-item")) {
    best = $(".nav-item.current") || best;
  }
  if (best) { best.focus(); best.scrollIntoView({ block: "nearest", inline: "nearest" }); }
}

document.addEventListener("keydown", e => {
  const el = document.activeElement;
  const typing = el && el.tagName === "INPUT";
  const dirs = { ArrowLeft: "left", ArrowRight: "right", ArrowUp: "up", ArrowDown: "down" };
  if (dirs[e.key]) {
    if (typing && (e.key === "ArrowLeft" || e.key === "ArrowRight")) return;
    e.preventDefault(); move(dirs[e.key]); return;
  }
  if (e.key === "Escape" || e.key === "BrowserBack" || e.key === "GoBack" || (e.key === "Backspace" && !typing)) {
    e.preventDefault();
    if (dialogOpen()) closeDialog(); else if (storeOpen()) closeStore(); else if (settingsOpen()) closeSettings();
    return;
  }
  if (e.key === "Enter" && typing) { e.preventDefault(); ($("#site-add") || $('#dialog [data-wact="connect"]')) && ($("#site-add") || $('#dialog [data-wact="connect"]')).click(); return; }
  if ((e.key === "ContextMenu" || e.key === "m") && el && el.classList.contains("banner")) {
    e.preventDefault(); appOptions(el.dataset.id); return;
  }
  if (e.key === "Enter" && el && el.classList.contains("banner") && !dialogOpen()) {
    e.preventDefault();
    if (e.repeat || holdTimer) return;
    const id = el.dataset.id;
    holdTimer = setTimeout(() => { holdTimer = "held"; appOptions(id); }, 650);
  }
});
document.addEventListener("keyup", e => {
  if (e.key !== "Enter" || !holdTimer) return;
  const el = document.activeElement;
  if (holdTimer !== "held") { clearTimeout(holdTimer); if (el && el.classList.contains("banner")) openApp(el.dataset.id); }
  holdTimer = null;
});

api("/api/state").then(r => { S = r; tick(); setInterval(tick, 10000); setWallpaper(); renderHome(); });
</script>
</body>
</html>
"""


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        setup()
    else:
        run()
