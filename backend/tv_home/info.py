"""System info: ported from v1's about()/display_name()/ip_address()."""
import os
import pwd
import re
import shutil
import subprocess
from pathlib import Path

from .config import VERSION


def run_cmd(args: list[str], timeout: int = 20) -> tuple[int, str, str]:
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except FileNotFoundError:
        return 127, "", f"{args[0]} is not installed."
    except subprocess.TimeoutExpired:
        return 124, "", "That took too long. Try again."


def ip_address() -> str:
    code, out, _ = run_cmd(["hostname", "-I"], 5)
    return out.split()[0] if code == 0 and out.split() else ""


def display_name() -> str:
    try:
        gecos = pwd.getpwuid(os.getuid()).pw_gecos.split(",")[0].strip()
        if gecos:
            return gecos.split()[0]
    except Exception:
        pass
    return os.environ.get("USER", "").capitalize()


def about() -> dict:
    info: dict = {}
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
        total, avail = int(mem["MemTotal"]) / 1_048_576, int(mem["MemAvailable"]) / 1_048_576
        info["memory"] = f"{total - avail:.1f} GB used of {total:.1f} GB"
    except Exception:
        info["memory"] = ""
    try:
        du = shutil.disk_usage("/")
        info["storage"] = f"{du.free / 1e9:.0f} GB free of {du.total / 1e9:.0f} GB"
    except Exception:
        info["storage"] = ""
    info["ip"] = ip_address() or "Not connected"
    info["version"] = VERSION
    return info
