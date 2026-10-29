"""chrome.py's PID-matching logic needs a real /proc (Linux-only), so these
only check it degrades safely without one — the actual matching was verified
by code review (see chrome.py's _kiosk_chrome_pids) after finding that
go_home() deliberately excludes the shell window (by design, for the Home
key) while the old "Go to desktop" implementation never closed anything in
its place, just killed the backend process — leaving tv-home-session.sh's
blocking wait on the still-running shell window with nothing to act on."""
from tv_home import chrome


def test_go_home_degrades_without_proc():
    ok, message = chrome.go_home()
    assert ok
    assert message == "No app is open."


def test_close_shell_degrades_without_proc():
    assert chrome.close_shell() is False


def test_close_shell_and_go_home_are_distinct_functions():
    # Regression guard for the actual bug: Power > Go to desktop needs a way
    # to close TV Home's *own* window, separate from go_home()'s "close
    # whatever app is open, but never the shell" behaviour.
    assert chrome.close_shell is not chrome.go_home
