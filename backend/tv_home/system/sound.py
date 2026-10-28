"""Real Sound backend: wpctl (PipeWire), per the PRD's stack table. Ported from
v1's sound_state()/sound_action() — only used when TV_HOME_MOCK is unset, so it
only ever runs on the real Linux box with PipeWire installed.

NOT RUNNABLE OR TESTED on this macOS sandbox (no wpctl/PipeWire here) — written
to spec from v1's working implementation; verify on the real PC.
"""
import asyncio
import re

SINK = "@DEFAULT_AUDIO_SINK@"


async def _run(args: list[str], timeout: float = 20) -> tuple[int, str, str]:
    try:
        proc = await asyncio.create_subprocess_exec(*args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return proc.returncode or 0, out.decode(errors="ignore"), err.decode(errors="ignore")
    except FileNotFoundError:
        return 127, "", f"{args[0]} is not installed."
    except asyncio.TimeoutError:
        return 124, "", "That took too long. Try again."


async def get_state() -> dict:
    code, out, _ = await _run(["wpctl", "get-volume", SINK])
    m = re.search(r"Volume:\s*([\d.]+)", out)
    if code or not m:
        return {"available": False, "error": "Sound settings aren't available on this PC.", "volume": 0, "muted": False, "outputs": []}
    outputs, in_audio, in_sinks = [], False, False
    _, status_out, _ = await _run(["wpctl", "status"])
    for raw in status_out.splitlines():
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
    return {
        "available": True,
        "volume": round(float(m.group(1)) * 100),
        "muted": "MUTED" in out,
        "outputs": outputs,
    }


async def action(kind: str, output_id: str | None = None) -> tuple[bool, str]:
    if kind == "up":
        await _run(["wpctl", "set-volume", "-l", "1.0", SINK, "5%+"])
    elif kind == "down":
        await _run(["wpctl", "set-volume", SINK, "5%-"])
    elif kind == "mute":
        await _run(["wpctl", "set-mute", SINK, "toggle"])
    elif kind == "output" and output_id and output_id.isdigit():
        await _run(["wpctl", "set-default", output_id])
    else:
        return False, "Unknown action."
    return True, ""
