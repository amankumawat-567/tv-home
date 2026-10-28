"""Date/time status. Uses timedatectl when present (the real PC, via
systemd-timesyncd); falls back to a simple sanity check elsewhere (this macOS
sandbox has no timedatectl) so `clockWrong` still means something in mock mode —
the PRD's dead-CMOS-battery scenario this is meant to catch (the clock resets to
some default past date after a power loss) would trip this fallback too."""
import datetime
import shutil
import subprocess

MIN_SANE_YEAR = 2024


def _run(args: list[str], timeout: int = 5) -> tuple[int, str]:
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout
    except Exception:
        return 1, ""


def get_state() -> dict:
    now = datetime.datetime.now()
    tz = str(now.astimezone().tzinfo)
    if shutil.which("timedatectl"):
        code, out = _run(["timedatectl", "show", "--property=NTPSynchronized,Timezone"])
        if code == 0:
            props = dict(line.split("=", 1) for line in out.splitlines() if "=" in line)
            return {
                "ntpSynced": props.get("NTPSynchronized") == "yes",
                "timezone": props.get("Timezone", tz),
                "clockWrong": now.year < MIN_SANE_YEAR,
            }
    return {"ntpSynced": True, "timezone": tz, "clockWrong": now.year < MIN_SANE_YEAR}
