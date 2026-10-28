from tv_home import apps


def test_install_then_appears_in_apps_view():
    ok, message = apps.install("Example", "example.com")
    assert ok
    assert "Example" in message
    view = apps.apps_view()
    assert len(view) == 1
    assert view[0]["name"] == "Example"
    assert view[0]["domain"] == "example.com"


def test_install_normalizes_url_and_rejects_duplicate():
    # norm_url lowercases and strips the trailing slash but doesn't unify
    # http/https (ported as-is from v1) — same scheme, different case, is the
    # duplicate case it actually catches.
    apps.install("Example", "https://example.com/")
    ok, message = apps.install("Example Again", "HTTPS://EXAMPLE.com")
    assert not ok
    assert "already" in message


def test_install_requires_name_and_url():
    ok, message = apps.install("", "https://example.com")
    assert not ok
    ok, message = apps.install("Name", "")
    assert not ok


def test_remove_unknown_app_fails_gracefully():
    ok, message = apps.remove("does-not-exist")
    assert not ok


def test_move_reorders_apps():
    apps.install("First", "first.com")
    apps.install("Second", "second.com")
    ids = [a["id"] for a in apps.load_apps()]
    ok, _ = apps.move(ids[1], "left")
    assert ok
    assert [a["id"] for a in apps.load_apps()] == [ids[1], ids[0]]


def test_move_past_the_edge_is_a_noop_not_a_crash():
    apps.install("Only", "only.com")
    [app] = apps.load_apps()
    ok, _ = apps.move(app["id"], "left")
    assert not ok
    assert apps.load_apps() == [app]


def test_catalog_view_reflects_install_state():
    before = apps.catalog_view()
    assert all(not c["installed"] for c in before)
    apps.install_from_catalog("netflix")
    after = apps.catalog_view()
    assert next(c for c in after if c["id"] == "netflix")["installed"]
