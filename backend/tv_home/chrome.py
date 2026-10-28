"""Launching and closing kiosk Chrome windows.

`go_home` is ported close to verbatim from v1's tv-home.py: it was a hard-won
fix (see the PRD's "Lessons learned" — Chrome rewrites its own process title,
so matching by argv string alone is unreliable; identifying the binary via
/proc/<pid>/exe is what made closing apps reliable).
"""
import os
import shutil
import signal
import subprocess
from pathlib import Path
from typing import Optional

from .apps import load_apps
from .config import PROFILE


def find_chrome() -> Optional[str]:
    # Deliberately PATH-only, matching the real Linux target (Chrome is always
    # on PATH there under one of these names). Not resolving macOS's Chrome.app
    # here is intentional: this backend also runs during local/dev testing on
    # macOS, and launching real GUI Chrome windows as a side effect of running
    # tests would leave stray windows behind that go_home() can't close on
    # macOS (it closes kiosk windows via /proc, Linux-only). The frontend's
    # own launch-screen UI is still fully testable without a real launch
    # succeeding — see frontend/tests/e2e/home.spec.ts.
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        path = shutil.which(name)
        if path:
            return path
    return None


def launch(app_id: str) -> tuple[bool, str]:
    app = next((a for a in load_apps() if a["id"] == app_id), None)
    if not app:
        return False, "That app isn't on your home screen."
    chrome = find_chrome()
    if not chrome:
        return False, "Google Chrome isn't installed."
    cmd = [chrome, "--kiosk", "--password-store=basic"]
    if app.get("ua"):
        cmd.append(f"--user-agent={app['ua']}")
    cmd.append(app["url"])
    subprocess.Popen(cmd, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return True, f"Opening {app['name']}"


def go_home() -> tuple[bool, str]:
    """Close every kiosk Chrome window that isn't this backend's own shell window."""
    closed = 0
    for pid in os.listdir("/proc") if os.path.isdir("/proc") else []:
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
