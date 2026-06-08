"""Pure helpers for role-aware UI gating. The backend remains authoritative for
authorization — these only decide which controls to render."""


def can_manage_catalog(user: dict | None) -> bool:
    """True if the user may create/update/delete exercises."""
    if not user:
        return False
    return "exercises:write" in user.get("scopes", [])


def is_admin(user: dict | None) -> bool:
    return bool(user) and user.get("role") == "admin"


def history_scope_label(user: dict | None) -> str:
    """What the History tab shows for this user."""
    if is_admin(user):
        return "all athletes' workout history"
    return "your workout history"
