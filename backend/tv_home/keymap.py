"""Remote key remapping with a learn mode (I3). The actual key *capture*
happens in the browser (KeyboardEvent is a DOM concept) — this module just
persists the resulting mapping of logical action -> physical key name, the
same way every other one-off preference lives in settings.json.

A null/missing entry means "use the built-in defaults for this action" (see
frontend/src/state/keymap.ts) — remapping one button doesn't require
re-specifying the rest.
"""
from typing import Optional

from . import config
from .state_store import read_json, write_json

ACTIONS = ("up", "down", "left", "right", "select", "back", "home", "menu")


def get_keymap() -> dict[str, Optional[str]]:
    stored = read_json(config.SETTINGS_FILE, {}).get("keymap", {})
    return {action: stored.get(action) for action in ACTIONS}


def set_key(action: str, key: Optional[str]) -> dict[str, Optional[str]]:
    if action not in ACTIONS:
        raise ValueError(f"Unknown action: {action}")
    settings = read_json(config.SETTINGS_FILE, {})
    keymap = settings.get("keymap", {})
    if key is None:
        keymap.pop(action, None)
    else:
        keymap[action] = key
    settings["keymap"] = keymap
    write_json(config.SETTINGS_FILE, settings)
    return get_keymap()


def reset() -> dict[str, Optional[str]]:
    settings = read_json(config.SETTINGS_FILE, {})
    settings["keymap"] = {}
    write_json(config.SETTINGS_FILE, settings)
    return get_keymap()
