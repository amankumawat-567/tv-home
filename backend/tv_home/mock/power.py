"""Fake Power backend used when TV_HOME_MOCK=1 — never touches the real host;
just reports what it would have done, so the confirm-dialog flow is testable
without risking a sleep/reboot/shutdown of the dev machine."""

_MESSAGES = {
    "sleep": "(mock) Would put the PC to sleep.",
    "restart": "(mock) Would restart the PC.",
    "poweroff": "(mock) Would shut the PC down.",
    "desktop": "(mock) Would exit to the desktop.",
}


async def action(kind: str) -> tuple[bool, str]:
    if kind not in _MESSAGES:
        return False, "Unknown action."
    return True, _MESSAGES[kind]
