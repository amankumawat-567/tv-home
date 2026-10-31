"""Launching and closing kiosk Chrome windows.

`go_home` is ported close to verbatim from v1's tv-home.py: it was a hard-won
fix (see the PRD's "Lessons learned" — Chrome rewrites its own process title,
so matching by argv string alone is unreliable; identifying the binary via
/proc/<pid>/exe is what made closing apps reliable).
"""
import asyncio
import os
import shutil
import signal
import subprocess
from pathlib import Path
from typing import Optional

from . import config

# SIGTERM asks Chrome to shut down gracefully, but on this hardware that can
# take far longer than expected -- a kiosk profile accumulating cache/cookies/
# service-worker state flushed to a slow old disk, or just one hung renderer,
# can leave the browser process alive for a long time after SIGTERM, which
# directly delays "Go to desktop" (tv-home-session.sh's foreground wait on
# this exact process) and the Home key for however long that takes. Give it a
# short grace period, then SIGKILL -- unconditional at the OS level, so it
# can't be slow for the same reasons SIGTERM can be.
_KILL_GRACE_SECONDS = 2.0


def _alive(pid: int) -> bool:
    # A launched app's Chrome is our own child (spawned via subprocess.Popen
    # in launch() below, never awaited since nothing keeps that Popen object
    # around) -- once it exits it becomes a zombie until reaped, and kill(pid,
    # 0) alone can't tell "still running" from "zombie, nobody's called wait()
    # on it yet", which would otherwise make every close here sit out the
    # full grace period even when Chrome exits instantly. Reap it here first.
    # The shell window is a child of tv-home-session.sh, not of us -- for
    # that PID waitpid() raises ECHILD, which just means "not our child, fall
    # through to the kill check" (the actual parent reaps it promptly, since
    # bash is blocked waiting on it as its own foreground command).
    try:
        os.waitpid(pid, os.WNOHANG)
    except OSError:
        pass
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


async def _terminate(pids: list[int]) -> None:
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except Exception:
            pass
    if not pids:
        return
    loop = asyncio.get_event_loop()
    deadline = loop.time() + _KILL_GRACE_SECONDS
    while loop.time() < deadline:
        if not any(_alive(pid) for pid in pids):
            return
        await asyncio.sleep(0.1)
    for pid in pids:
        try:
            os.kill(pid, signal.SIGKILL)
        except Exception:
            pass
from .apps import load_apps


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


def _kiosk_chrome_pids(*, want_shell: bool) -> list[int]:
    """PIDs of kiosk Chrome processes, split by whether they're this backend's
    own shell window (user-data-dir == PROFILE) or a launched app's. Chrome
    rewrites its own process title, so matching by argv alone is unreliable —
    /proc/<pid>/exe identifies the real binary regardless."""
    pids = []
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
        if "--kiosk" not in cmd or "--type=" in cmd:
            continue
        is_shell = str(config.PROFILE) in cmd
        if is_shell == want_shell:
            pids.append(int(pid))
    return pids


async def go_home() -> tuple[bool, str]:
    """Close every kiosk Chrome window that isn't this backend's own shell window."""
    pids = _kiosk_chrome_pids(want_shell=False)
    await _terminate(pids)
    return True, "" if pids else "No app is open."


async def close_shell() -> bool:
    """Close TV Home's own shell window — the one go_home() deliberately
    leaves alone. Used by Power > Go to desktop so tv-home-session.sh's
    foreground `chrome ... "$BACKEND_URL/"` returns and its sentinel check
    (session/tv-home-session.sh) can hand off to the regular desktop; without
    this, killing only the backend left the shell window running with
    nothing to talk to, and the session script stayed blocked waiting for a
    window that was never going to exit on its own."""
    pids = _kiosk_chrome_pids(want_shell=True)
    await _terminate(pids)
    return bool(pids)
