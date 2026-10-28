"""Fake Sound backend used when TV_HOME_MOCK=1 — mirrors system/sound.py
(wpctl/PipeWire)'s shape."""
_state = {"volume": 40, "muted": False, "current": "hdmi"}
_OUTPUTS = [("hdmi", "HDMI Audio"), ("speakers", "Built-in Speakers"), ("bt", "Bluetooth Speaker")]


async def get_state() -> dict:
    outputs = [{"id": oid, "name": name, "current": oid == _state["current"]} for oid, name in _OUTPUTS]
    return {"available": True, "volume": _state["volume"], "muted": _state["muted"], "outputs": outputs}


async def action(kind: str, output_id: str | None = None) -> tuple[bool, str]:
    if kind == "up":
        _state["volume"] = min(100, _state["volume"] + 5)
    elif kind == "down":
        _state["volume"] = max(0, _state["volume"] - 5)
    elif kind == "mute":
        _state["muted"] = not _state["muted"]
    elif kind == "output" and output_id:
        _state["current"] = output_id
    else:
        return False, "Unknown action."
    return True, ""
