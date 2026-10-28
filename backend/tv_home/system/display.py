"""Real Display backend: xrandr for resolution, xset for the screen-off timer.

NOT RUNNABLE OR TESTED on this macOS sandbox (no X11/xrandr here) — written to
spec; verify on the real PC. The 15s auto-revert is enforced by the route layer
(routes/display.py), which calls `revert_if_unconfirmed` on a timer — this
module only applies/reads the mode xrandr reports right now.
"""
import asyncio
import re
import time
import uuid

_pending: dict[str, dict] = {}


async def _run(args: list[str], timeout: float = 20) -> tuple[int, str, str]:
    try:
        proc = await asyncio.create_subprocess_exec(*args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return proc.returncode or 0, out.decode(errors="ignore"), err.decode(errors="ignore")
    except FileNotFoundError:
        return 127, "", f"{args[0]} is not installed."
    except asyncio.TimeoutError:
        return 124, "", "That took too long. Try again."


def _primary_output(xrandr_out: str) -> str | None:
    m = re.search(r"^(\S+) connected", xrandr_out, re.M)
    return m.group(1) if m else None


async def get_state() -> dict:
    code, out, _ = await _run(["xrandr"])
    if code:
        return {"available": False, "error": "Display settings aren't available on this PC.", "modes": [], "screenOffMinutes": 0}
    output = _primary_output(out)
    if not output:
        return {"available": False, "error": "No connected display found.", "modes": [], "screenOffMinutes": 0}

    modes = []
    in_output = False
    for line in out.splitlines():
        if line.startswith(output):
            in_output = True
            continue
        if in_output:
            if not line.startswith(" "):
                break
            m = re.match(r"^\s*(\d+x\d+)\S*\s+([\d.]+)(\*?)", line)
            if m:
                res, rate, current = m.group(1), m.group(2), m.group(3) == "*"
                modes.append({"id": f"{res}@{rate}", "label": f"{res} @ {round(float(rate))}Hz", "current": current})

    timer_code, timer_out, _ = await _run(["xset", "q"])
    off_minutes = 0
    if not timer_code:
        m = re.search(r"Standby:\s*(\d+)", timer_out)
        if m:
            off_minutes = int(m.group(1)) // 60
    return {"available": True, "modes": modes, "screenOffMinutes": off_minutes}


async def set_mode(mode_id: str) -> tuple[bool, str]:
    code, out, _ = await _run(["xrandr"])
    output = _primary_output(out)
    if not output:
        return False, ""
    res = mode_id.split("@")[0]
    code, _, err = await _run(["xrandr", "--output", output, "--mode", res])
    if code:
        return False, err or "Couldn't change the resolution."
    token = uuid.uuid4().hex
    _pending[token] = {"mode": mode_id, "at": time.monotonic()}
    return True, token


async def confirm_mode(token: str) -> bool:
    return _pending.pop(token, None) is not None


async def revert_if_unconfirmed(token: str) -> None:
    pending = _pending.pop(token, None)
    if not pending:
        return
    code, out, _ = await _run(["xrandr"])
    output = _primary_output(out)
    # Revert to whatever mode is marked "preferred" (the '+' flag in xrandr output).
    if output:
        m = re.search(rf"{re.escape(output)}.*?\n((?:\s+\S.*\n?)*)", out)
        if m:
            pref = re.search(r"^\s*(\d+x\d+)\S*\s+[\d.]+\+", m.group(1), re.M)
            if pref:
                await _run(["xrandr", "--output", output, "--mode", pref.group(1)])


async def set_screen_off(minutes: int) -> tuple[bool, str]:
    seconds = minutes * 60
    code, _, err = await _run(["xset", "s", str(seconds), str(seconds), "dpms", str(seconds), str(seconds), str(seconds)])
    return code == 0, "" if code == 0 else (err or "Couldn't change the screen-off timer.")
