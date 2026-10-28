"""Picks the mock or real implementation of each system integration, once, at
import time — so the real system/* modules (which import dbus-fast, Linux-only)
are never even imported when TV_HOME_MOCK=1, and routes stay oblivious to which
one they're calling through.
"""
from . import config

if config.MOCK:
    from .mock import bluetooth as bluetooth_provider
    from .mock import display as display_provider
    from .mock import power as power_provider
    from .mock import sound as sound_provider
    from .mock import update as update_provider
    from .mock import wifi as wifi_provider
else:
    from .system import bluetooth as bluetooth_provider
    from .system import display as display_provider
    from .system import power as power_provider
    from .system import sound as sound_provider
    from .system import update as update_provider
    from .system import wifi as wifi_provider

__all__ = [
    "wifi_provider",
    "bluetooth_provider",
    "sound_provider",
    "display_provider",
    "power_provider",
    "update_provider",
]
