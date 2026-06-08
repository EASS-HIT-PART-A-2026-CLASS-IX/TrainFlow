from permissions import can_manage_catalog, history_scope_label, is_admin

ADMIN = {"username": "admin", "role": "admin",
         "scopes": ["exercises:write", "history:read", "history:write", "coach:use"]}
ATHLETE = {"username": "alice", "role": "athlete",
           "scopes": ["history:read", "history:write", "coach:use"]}


def test_admin_can_manage_catalog():
    assert can_manage_catalog(ADMIN) is True


def test_athlete_cannot_manage_catalog():
    assert can_manage_catalog(ATHLETE) is False


def test_none_user_cannot_manage_catalog():
    assert can_manage_catalog(None) is False


def test_is_admin():
    assert is_admin(ADMIN) is True
    assert is_admin(ATHLETE) is False
    assert is_admin(None) is False


def test_history_scope_label():
    assert "all" in history_scope_label(ADMIN)
    assert "your" in history_scope_label(ATHLETE)
