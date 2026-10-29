"""Tracks whether the first-run setup wizard (Y4: Wi-Fi, pair a remote, pick
apps) has been completed, so it only ever shows once — persisted the same way
as every other one-off preference, in settings.json."""
from . import config
from .state_store import read_json, write_json


def is_complete() -> bool:
    return bool(read_json(config.SETTINGS_FILE, {}).get("firstRunComplete", False))


def mark_complete() -> None:
    settings = read_json(config.SETTINGS_FILE, {})
    settings["firstRunComplete"] = True
    write_json(config.SETTINGS_FILE, settings)
