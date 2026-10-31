import asyncio

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def client():
    from tv_home.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_state_shape(client):
    res = await client.get("/api/state")
    assert res.status_code == 200
    body = res.json()
    assert set(body) == {"user", "wallpaper", "wallpaperVersion", "apps", "catalog", "firstRunComplete", "status"}
    assert set(body["status"]) == {"wifi", "bluetooth", "volume", "muted", "clockWrong"}


@pytest.mark.asyncio
async def test_install_and_remove_roundtrip(client):
    res = await client.post("/api/apps", json={"name": "Example", "url": "https://example.com"})
    assert res.json()["ok"]
    assert len(res.json()["apps"]) == 1
    app_id = res.json()["apps"][0]["id"]

    res = await client.delete(f"/api/apps/{app_id}")
    assert res.json()["ok"]
    assert res.json()["apps"] == []


@pytest.mark.asyncio
async def test_launch_unknown_app_fails(client):
    res = await client.post("/api/apps/does-not-exist/launch")
    assert res.json()["ok"] is False


@pytest.mark.asyncio
async def test_wifi_mock_flow(client):
    res = await client.get("/api/wifi")
    data = res.json()
    assert data["available"]
    assert any(n["ssid"] == "Cafe Guest" for n in data["networks"])

    res = await client.post("/api/wifi/connect", json={"ssid": "Cafe Guest"})
    assert res.json()["ok"]


@pytest.mark.asyncio
async def test_wifi_wrong_password_reports_plain_language_error(client):
    res = await client.post("/api/wifi/connect", json={"ssid": "Home Network", "password": "wrong"})
    body = res.json()
    assert not body["ok"]
    assert "password" in body["message"].lower()


@pytest.mark.asyncio
async def test_bluetooth_no_adapter_state(client, monkeypatch):
    from tv_home.mock import bluetooth as bt

    monkeypatch.setitem(bt._state, "hasAdapter", False)
    res = await client.get("/api/bluetooth")
    body = res.json()
    assert body["available"] is False
    assert "adapter" in body["error"].lower()


@pytest.mark.asyncio
async def test_sound_volume_steps(client):
    before = (await client.get("/api/sound")).json()["volume"]
    await client.post("/api/sound", json={"action": "up"})
    after = (await client.get("/api/sound")).json()["volume"]
    assert after == before + 5


@pytest.mark.asyncio
async def test_display_set_mode_returns_token_and_confirm_accepts_it(client):
    modes = (await client.get("/api/display")).json()["modes"]
    target = next(m for m in modes if not m["current"])
    res = await client.post("/api/display", json={"id": target["id"]})
    body = res.json()
    assert body["ok"]
    assert body["token"]

    res = await client.post("/api/display/confirm", json={"token": body["token"]})
    assert res.json()["ok"]


@pytest.mark.asyncio
async def test_power_mock_never_touches_the_real_host(client):
    for action in ("poweroff", "restart", "sleep", "desktop"):
        res = await client.post("/api/power", json={"action": action})
        body = res.json()
        assert body["ok"], f"{action} should succeed in mock mode"
        assert "(mock)" in body["message"]


@pytest.mark.asyncio
async def test_update_check_and_apply_roundtrip(client):
    res = await client.get("/api/update")
    body = res.json()
    assert body["available"]
    assert body["url"]

    res = await client.post("/api/update/apply", json={})
    body = res.json()
    assert body["ok"]

    # Once "applied", the mock update provider reports up to date.
    res = await client.get("/api/update")
    assert res.json()["available"] is False


@pytest.mark.asyncio
async def test_about_includes_the_version_from_the_VERSION_file(client):
    res = await client.get("/api/about")
    assert res.json()["version"]


@pytest.mark.asyncio
async def test_launch_inhibits_screen_off_and_home_restores_it(client):
    from tv_home.mock import display as disp

    assert disp._state["inhibited"] is False

    install = (await client.post("/api/apps", json={"id": "netflix", "name": "Netflix", "url": ""})).json()
    app_id = install["apps"][0]["id"]

    # A real Chrome binary isn't on PATH in this sandbox, so the launch call
    # itself reports failure (see backend/tv_home/chrome.py) — but the mock
    # display provider's inhibit() is wired to fire on `ok`, which this
    # environment never satisfies. Call the route handler's own dependency
    # directly to verify the plumbing instead of the unreachable success path.
    from tv_home.providers import display_provider

    await display_provider.inhibit()
    assert disp._state["inhibited"] is True

    await client.post("/api/home")
    assert disp._state["inhibited"] is False


@pytest.mark.asyncio
async def test_display_screen_off_minutes_persists_across_inhibit(client):
    await client.post("/api/display/screen-off", json={"minutes": 15})
    assert (await client.get("/api/display")).json()["screenOffMinutes"] == 15

    from tv_home.providers import display_provider

    await display_provider.inhibit()
    # Settings > Display should still report the user's actual preference
    # while an app has it temporarily suspended, not "Never".
    assert (await client.get("/api/display")).json()["screenOffMinutes"] == 15

    await display_provider.restore()
    assert (await client.get("/api/display")).json()["screenOffMinutes"] == 15


@pytest.mark.asyncio
async def test_wallpaper_slideshow_persists(client):
    res = await client.get("/api/wallpaper/slideshow")
    assert res.json() == {"enabled": False, "minutes": 15}

    res = await client.post("/api/wallpaper/slideshow", json={"enabled": True, "minutes": 30})
    assert res.json() == {"enabled": True, "minutes": 30}

    # Persists across requests (settings.json), not just in-memory for one call.
    res = await client.get("/api/wallpaper/slideshow")
    assert res.json() == {"enabled": True, "minutes": 30}

    # Toggling off keeps the chosen interval.
    res = await client.post("/api/wallpaper/slideshow", json={"enabled": False})
    assert res.json() == {"enabled": False, "minutes": 30}


def _seed_wallpapers(names: list[str]) -> None:
    # wallpapers() ignores anything under 100KB (see its own docstring-less
    # size check) to skip thumbnails/junk, so test fixtures have to actually
    # clear that bar. Each file's content is distinct (keyed by its own name)
    # so a test comparing "did this serve the right one" can't pass by
    # accident just because every fixture happened to be identical bytes.
    from tv_home import config

    config.USER_WALLS.mkdir(parents=True, exist_ok=True)
    for name in names:
        (config.USER_WALLS / name).write_bytes(name.encode() + b"\xff" * 150_000)


@pytest.mark.asyncio
async def test_wallpaper_list_and_set(client):
    _seed_wallpapers(["ocean-view.jpg", "city-night.jpg", "forest-path.jpg"])

    res = await client.get("/api/wallpaper/list")
    body = res.json()
    assert body["current"] == 0
    # wallpapers() sorts by path, i.e. alphabetically -- not insertion order.
    assert [item["name"] for item in body["items"]] == ["City Night", "Forest Path", "Ocean View"]

    res = await client.post("/api/wallpaper/set", json={"index": 2})
    assert res.json()["current"] == 2

    # The state broadcast's cache-busting token follows the selection.
    res = await client.get("/api/state")
    assert res.json()["wallpaperVersion"] == 2

    # /wallpaper (the "current" one) and /wallpaper/{index} both serve real
    # image bytes for the selected/given index.
    res = await client.get("/wallpaper")
    assert res.status_code == 200
    assert res.headers["cache-control"] == "no-store"
    current_bytes = res.content

    res = await client.get("/wallpaper/2")
    assert res.status_code == 200
    assert res.content == current_bytes

    res = await client.get("/wallpaper/99")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_wallpaper_next_wraps_and_broadcasts(client):
    _seed_wallpapers(["a.jpg", "b.jpg"])
    assert (await client.get("/api/wallpaper/list")).json()["current"] == 0

    await client.post("/api/wallpaper")
    assert (await client.get("/api/wallpaper/list")).json()["current"] == 1

    await client.post("/api/wallpaper")  # wraps back to the first
    assert (await client.get("/api/wallpaper/list")).json()["current"] == 0


@pytest.mark.asyncio
async def test_first_run_wizard_shows_once(client):
    res = await client.get("/api/state")
    assert res.json()["firstRunComplete"] is False

    res = await client.post("/api/first-run/complete")
    assert res.json()["ok"]

    # Persists (settings.json), so it doesn't come back on the next request —
    # unlike a plain in-memory flag, which would reset per test anyway.
    res = await client.get("/api/state")
    assert res.json()["firstRunComplete"] is True


@pytest.mark.asyncio
async def test_keymap_remap_persists_and_resets(client):
    res = await client.get("/api/input/keymap")
    body = res.json()
    assert set(body) == {"up", "down", "left", "right", "select", "back", "home", "menu"}
    assert body["home"] is None  # unconfigured -> frontend falls back to its built-in defaults

    res = await client.post("/api/input/keymap", json={"action": "home", "key": "F1"})
    assert res.json()["home"] == "F1"
    # Remapping one action leaves the others alone.
    assert res.json()["back"] is None

    res = await client.get("/api/input/keymap")
    assert res.json()["home"] == "F1"

    res = await client.post("/api/input/keymap/reset")
    assert res.json()["home"] is None


@pytest.mark.asyncio
async def test_keymap_rejects_unknown_action(client):
    res = await client.post("/api/input/keymap", json={"action": "jump", "key": "J"})
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_phone_typing_round_trip(client):
    res = await client.post("/api/type/start")
    body = res.json()
    token = body["token"]
    assert token in body["url"]
    assert body["url"].startswith("http://")

    # TV side polls this — starts empty, not done.
    res = await client.get(f"/api/type/{token}")
    assert res.json() == {"value": "", "done": False}

    # Phone side posts as the user types (no /api prefix — this is the path
    # opened directly from the QR code, served to the phone's own browser).
    res = await client.post(f"/type/{token}", json={"value": "hello"})
    assert res.json()["ok"]

    res = await client.get(f"/api/type/{token}")
    assert res.json() == {"value": "hello", "done": False}

    # Phone taps "Done".
    res = await client.post(f"/type/{token}/done")
    assert res.json()["ok"]
    res = await client.get(f"/api/type/{token}")
    assert res.json() == {"value": "hello", "done": True}

    # The TV-facing page itself renders (what the QR code's URL points at).
    res = await client.get(f"/type/{token}")
    assert res.status_code == 200
    assert token in res.text


@pytest.mark.asyncio
async def test_phone_typing_unknown_token_is_a_clean_404(client):
    assert (await client.get("/api/type/does-not-exist")).status_code == 404
    assert (await client.post("/type/does-not-exist", json={"value": "x"})).status_code == 404
    assert (await client.post("/type/does-not-exist/done")).status_code == 404
    assert (await client.get("/type/does-not-exist")).status_code == 404


@pytest.mark.asyncio
async def test_bluetooth_pin_pairing_round_trip(client):
    # connect() blocks for the whole handshake, same as the real BlueZ agent
    # would -- drive it concurrently with the side-channel pairing poll/respond,
    # exactly how the frontend has to.
    mac, name = "AA:BB:CC:00:11:55", "Old Bluetooth Keyboard"

    async def wait_for_pending():
        for _ in range(50):
            pending = (await client.get("/api/bluetooth/pairing")).json()
            if pending:
                return pending
            await asyncio.sleep(0.02)
        raise AssertionError("pairing request never appeared")

    # Wrong PIN -- pairing fails, device stays unpaired.
    connect_task = asyncio.create_task(client.post("/api/bluetooth/connect", json={"mac": mac, "name": name}))
    pending = await wait_for_pending()
    assert pending == {"mac": mac, "name": name, "kind": "pin", "passkey": None}
    await client.post("/api/bluetooth/pairing/respond", json={"value": "9999"})
    result = (await connect_task).json()
    assert result["ok"] is False

    # Right PIN -- succeeds.
    connect_task = asyncio.create_task(client.post("/api/bluetooth/connect", json={"mac": mac, "name": name}))
    pending = await wait_for_pending()
    assert pending["kind"] == "pin"
    await client.post("/api/bluetooth/pairing/respond", json={"value": "0000"})
    result = (await connect_task).json()
    assert result["ok"] is True
    assert name in result["message"]


@pytest.mark.asyncio
async def test_bluetooth_passkey_confirmation_round_trip(client):
    mac, name = "AA:BB:CC:00:11:66", "Car Stereo"

    async def wait_for_pending():
        for _ in range(50):
            pending = (await client.get("/api/bluetooth/pairing")).json()
            if pending:
                return pending
            await asyncio.sleep(0.02)
        raise AssertionError("pairing request never appeared")

    # Reject -- fails, stays unpaired.
    connect_task = asyncio.create_task(client.post("/api/bluetooth/connect", json={"mac": mac, "name": name}))
    pending = await wait_for_pending()
    assert pending == {"mac": mac, "name": name, "kind": "confirm", "passkey": 583921}
    await client.post("/api/bluetooth/pairing/respond", json={"accept": False})
    assert (await connect_task).json()["ok"] is False

    # Accept -- succeeds.
    connect_task = asyncio.create_task(client.post("/api/bluetooth/connect", json={"mac": mac, "name": name}))
    pending = await wait_for_pending()
    assert pending["kind"] == "confirm"
    await client.post("/api/bluetooth/pairing/respond", json={"accept": True})
    result = (await connect_task).json()
    assert result["ok"] is True


@pytest.mark.asyncio
async def test_kdeconnect_state_shape(client):
    res = await client.get("/api/kdeconnect")
    assert res.status_code == 200
    body = res.json()
    assert body["available"] is True
    assert {"id", "name", "paired", "reachable", "incomingRequest"} <= set(body["devices"][0])


@pytest.mark.asyncio
async def test_kdeconnect_box_initiated_pairing(client):
    res = await client.post("/api/kdeconnect/pair", json={"id": "dev-pixel", "name": "Aman's Pixel"})
    body = res.json()
    assert body["ok"] is True
    devices = (await client.get("/api/kdeconnect")).json()["devices"]
    assert next(d for d in devices if d["id"] == "dev-pixel")["paired"] is True


@pytest.mark.asyncio
async def test_kdeconnect_accept_and_reject_incoming_request(client):
    res = await client.post("/api/kdeconnect/reject", json={"id": "dev-old-phone", "name": "Old Phone"})
    assert res.json()["ok"] is True
    devices = (await client.get("/api/kdeconnect")).json()["devices"]
    old_phone = next(d for d in devices if d["id"] == "dev-old-phone")
    assert old_phone["incomingRequest"] is False
    assert old_phone["paired"] is False


@pytest.mark.asyncio
async def test_kdeconnect_duplicate_names_distinguished_by_reachability(client):
    # Re-pairing a phone after reinstalling its KDE Connect app leaves a
    # stale duplicate with an identical name behind on the real PC -- the
    # API must expose reachability per-ID so the frontend can tell them
    # apart (it used to show "Paired" for both, which is how a user ended up
    # pushing the TV remote config to the wrong one).
    devices = (await client.get("/api/kdeconnect")).json()["devices"]
    laptops = [d for d in devices if d["name"] == "Office Laptop"]
    assert len(laptops) == 2
    assert {d["id"]: d["reachable"] for d in laptops} == {
        "272df33ad75442f4b0ea8d5abd88adc2": True,
        "199b325932ee4370a1600aa40c8c5ca4": False,
    }
    assert all(d["paired"] for d in laptops)


@pytest.mark.asyncio
async def test_kdeconnect_install_remote_on_already_paired_device(client):
    # The device-already-paired path: pair()/accept() only write the Run
    # Command config at the moment pairing happens, so anything paired
    # before that feature existed (or paired through some path other than
    # this app) never got it -- install-remote covers that without needing
    # an unpair/re-pair.
    res = await client.post("/api/kdeconnect/install-remote", json={"id": "272df33ad75442f4b0ea8d5abd88adc2", "name": "Office Laptop"})
    body = res.json()
    assert body["ok"] is True
    assert "Office Laptop" in body["message"]

    res = await client.post("/api/kdeconnect/install-remote", json={"id": "does-not-exist", "name": "Nothing"})
    assert res.json()["ok"] is False
