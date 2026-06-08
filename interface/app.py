import datetime as dt

import pandas as pd
import streamlit as st

import ui_styles as ui
from client import (
    BackendUnavailableError,
    coach_status,
    create_exercise,
    delete_exercise,
    get_me,
    list_exercises,
    list_sessions,
    log_session,
    login,
    register,
    request_plan,
    update_exercise,
)
from coach import EXPERIENCES, GOALS, build_plan_payload, plan_day_rows, resolve_avoid_ids
from export import generate_reference_sheet
from filters import apply_filters
from metrics import compute_dashboard_metrics
from permissions import can_manage_catalog, history_scope_label, is_admin

_MUSCLE_GROUPS = [
    "chest", "back", "shoulders", "biceps", "triceps",
    "core", "glutes", "calves", "forearms", "quadriceps", "hamstrings",
]
_EQUIPMENT = ["bodyweight", "dumbbell", "barbell", "machine", "cable", "smith"]
_DIFFICULTIES = ["beginner", "intermediate", "advanced"]
_TAGLINE = "AI-assisted workout planning from your real exercise catalog and training history"


# --------------------------------------------------------------------------- #
# Data + session helpers
# --------------------------------------------------------------------------- #
def _load_exercises() -> list[dict] | None:
    try:
        return list_exercises()
    except BackendUnavailableError:
        return None


def _md(html: str) -> None:
    st.markdown(html, unsafe_allow_html=True)


def _sign_in(token: str, username: str) -> None:
    st.session_state["token"] = token
    st.session_state["username"] = username
    try:
        st.session_state["user"] = get_me(token)
    except BackendUnavailableError:
        st.session_state["user"] = {"username": username, "role": "athlete", "scopes": []}
    st.session_state["exercises"] = _load_exercises()
    st.session_state["nav"] = "Dashboard"


def _goto(page: str) -> None:
    """Navigation callback — safe to set the nav widget's state here."""
    st.session_state["nav"] = page


def _catalog() -> list[dict]:
    return st.session_state.get("exercises") or []


def _grid(html_items: list[str], cols: int = 3) -> None:
    columns = st.columns(cols)
    for index, item in enumerate(html_items):
        with columns[index % cols]:
            _md(item)


# --------------------------------------------------------------------------- #
# Auth screen (unauthenticated)
# --------------------------------------------------------------------------- #
def _auth_screen() -> None:
    left, mid, right = st.columns([1, 1.4, 1])
    with mid:
        _md(ui.hero("TrainFlow Coach", _TAGLINE, center=True))
        st.write("")
        with st.container(border=True):
            mode = st.radio(
                "Mode", ["Log in", "Register"], horizontal=True, label_visibility="collapsed"
            )
            if mode == "Log in":
                _login_form()
            else:
                _register_form()


def _login_form() -> None:
    with st.form("login_form"):
        st.caption("Demo admin: admin / admin123")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in", width="stretch")
    if submitted:
        try:
            _sign_in(login(username, password), username)
            st.rerun()
        except ValueError:
            st.error("Incorrect username or password.")
        except BackendUnavailableError:
            st.error("Cannot reach the backend.")


def _register_form() -> None:
    with st.form("register_form"):
        st.caption("New accounts are created as athletes.")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        confirm = st.text_input("Confirm password", type="password")
        submitted = st.form_submit_button("Create account", width="stretch")
    if not submitted:
        return
    if not username.strip():
        st.warning("Username is required.")
        return
    if password != confirm:
        st.warning("Passwords do not match.")
        return
    try:
        register(username.strip(), password)
        _sign_in(login(username.strip(), password), username.strip())
        st.success("Account created — you are now signed in.")
        st.rerun()
    except ValueError as exc:
        st.error(f"Registration failed: {exc}")
    except BackendUnavailableError:
        st.error("Cannot reach the backend.")


# --------------------------------------------------------------------------- #
# Pages
# --------------------------------------------------------------------------- #
def _page_dashboard(user: dict, provider: str) -> None:
    token = st.session_state["token"]
    exercises = _catalog()
    try:
        sessions = list_sessions(token, limit=20)
    except BackendUnavailableError:
        sessions = []

    m = compute_dashboard_metrics(exercises, sessions)
    more_focus = max(0, m["focus_total"] - len(m["top_focus"]))

    cards = [
        ui.metric_card("Exercises", m["total_exercises"], "in catalog", accent=True),
        ui.metric_card("Workout sessions", m["total_sessions"], history_scope_label(user)),
        ui.metric_card("Equipment types", m["equipment_types"], "available"),
        ui.metric_chip_card("Recent focus", m["top_focus"], more_focus, "from your history"),
        ui.metric_card("Coach", ui.provider_label(provider), "active mode"),
    ]
    _grid(cards, cols=5)

    st.write("")
    _md(
        '<div class="tf-panel"><b>Ready to train?</b> &nbsp;Generate a structured, '
        "history-aware plan from your catalog in seconds.</div>"
    )
    st.button("Start with Coach", type="primary", on_click=_goto, args=("AI Coach",))


def _page_coach(user: dict, provider: str) -> None:
    token = st.session_state["token"]
    catalog = _catalog()
    catalog_by_id = {ex["id"]: ex for ex in catalog if "id" in ex}

    st.subheader("AI Coach")
    _md(ui.provider_badge(provider))
    form_col, result_col = st.columns([1, 1.3], gap="large")

    with form_col:
        with st.form("coach_form"):
            goal = st.selectbox("Goal", GOALS, index=1)
            experience = st.selectbox("Experience", EXPERIENCES, index=1)
            c1, c2 = st.columns(2)
            with c1:
                days_per_week = st.slider("Days / week", 1, 7, 3)
            with c2:
                session_minutes = st.slider("Minutes / session", 15, 120, 60, step=5)
            available_equipment = st.multiselect("Available equipment", _EQUIPMENT)
            target_muscles = st.multiselect("Focus muscles (likes)", _MUSCLE_GROUPS)
            avoid_names = st.multiselect(
                "Avoid exercises (dislikes)", [ex["name"] for ex in catalog]
            )
            submitted = st.form_submit_button("Generate plan", type="primary", width="stretch")

    if submitted:
        payload = build_plan_payload(
            goal=goal,
            experience=experience,
            days_per_week=days_per_week,
            session_minutes=session_minutes,
            available_equipment=available_equipment,
            target_muscles=target_muscles,
            avoid_exercise_ids=resolve_avoid_ids(avoid_names, catalog),
        )
        try:
            with st.spinner("Coach is designing your plan..."):
                st.session_state["last_plan"] = request_plan(payload, token)
        except BackendUnavailableError:
            st.session_state["last_plan"] = None
            st.error("Cannot reach the coach service. Is it running on port 8001?")
        except ValueError as exc:
            st.session_state["last_plan"] = None
            st.error(f"Coach error: {exc}")

    with result_col:
        plan = st.session_state.get("last_plan")
        if not plan:
            _md(ui.empty_state("No plan yet", "Set your goal and generate a plan to see it here."))
            return

        _md(ui.provider_badge(plan.get("generated_by", provider)))
        for insight in plan.get("insights", []):
            _md(ui.insight_panel(insight))
        for index, day in enumerate(plan.get("days", []), start=1):
            _md(ui.plan_day_card(index, day.get("focus", "Workout"), day.get("items", []), catalog_by_id))
        if plan.get("notes"):
            st.caption(plan["notes"])


def _page_catalog() -> None:
    st.subheader("Exercise Catalog")
    exercises = st.session_state.get("exercises")
    if exercises is None:
        st.error("Cannot reach the backend.")
        return

    with st.container(border=True):
        f1, f2, f3 = st.columns(3)
        with f1:
            muscles = st.multiselect("Muscle group", _MUSCLE_GROUPS)
        with f2:
            equipment = st.multiselect("Equipment", _EQUIPMENT)
        with f3:
            difficulties = st.multiselect("Difficulty", _DIFFICULTIES)

    filtered = apply_filters(exercises, muscles, equipment, difficulties)
    st.caption(f"{len(filtered)} exercise(s)")

    if not filtered:
        _md(ui.empty_state("No matches", "Try clearing a filter to see more exercises."))
        return

    _grid([ui.exercise_card(ex) for ex in filtered], cols=3)

    with st.expander("Export reference sheet (PNG)"):
        st.download_button(
            "Download PNG",
            data=generate_reference_sheet(filtered),
            file_name="trainflow_reference.png",
            mime="image/png",
        )


def _page_history(user: dict) -> None:
    token = st.session_state["token"]
    catalog = _catalog()
    by_id = {ex["id"]: ex for ex in catalog if "id" in ex}
    name_to_id = {ex["name"]: ex["id"] for ex in catalog if "id" in ex}

    st.subheader("Workout History")
    st.caption(f"Showing {history_scope_label(user)}.")

    try:
        sessions = list_sessions(token, limit=20)
    except BackendUnavailableError:
        st.error("Cannot reach the backend.")
        return

    if sessions:
        for s in sessions:
            lines = []
            for i in s["exercises"]:
                name = by_id.get(i["exercise_id"], {}).get(
                    "name", i.get("exercise_name", f"#{i['exercise_id']}")
                )
                weight = f" @ {i['weight']}kg" if i.get("weight") else ""
                lines.append(f"{name} — {i['sets']}×{i['reps']}{weight}")
            _md(ui.session_card(s, lines, show_owner=is_admin(user)))
    else:
        _md(ui.empty_state("No sessions yet", "Log your first workout below to personalize your coach."))

    with st.expander("Log a session"):
        with st.form("log_session_form"):
            date = st.date_input("Date", value=dt.date.today())
            goal = st.selectbox("Goal", GOALS, index=1)
            names = st.multiselect("Exercises", [ex["name"] for ex in catalog])
            c1, c2, c3 = st.columns(3)
            with c1:
                sets = st.number_input("Sets", min_value=1, max_value=10, value=3)
            with c2:
                reps = st.number_input("Reps", min_value=1, max_value=100, value=10)
            with c3:
                weight = st.number_input("Weight (kg, 0 = bodyweight)", min_value=0.0, value=0.0)
            submitted = st.form_submit_button("Log session", type="primary")
        if submitted:
            chosen = [name_to_id[n] for n in names if n in name_to_id]
            if not chosen:
                st.warning("Select at least one exercise.")
                return
            payload = {
                "date": date.isoformat(),
                "goal": goal,
                "exercises": [
                    {
                        "exercise_id": eid,
                        "sets": int(sets),
                        "reps": int(reps),
                        "weight": float(weight) if weight > 0 else None,
                    }
                    for eid in chosen
                ],
            }
            try:
                log_session(payload, token)
                st.success("Session logged.")
                st.rerun()
            except BackendUnavailableError:
                st.error("Cannot reach the backend.")
            except ValueError as exc:
                st.error(f"Could not log session: {exc}")


def _page_admin() -> None:
    token = st.session_state["token"]
    st.subheader("Admin · Catalog Management")
    st.caption("Create, update, and delete catalog exercises. Visible to admins only.")
    exercises = _catalog()

    with st.expander("Add exercise", expanded=True):
        _admin_add_form(token)
    with st.expander("Edit exercise"):
        _admin_edit_form(token, exercises)
    with st.expander("Delete exercise"):
        _admin_delete_form(token, exercises)


def _exercise_form_fields(prefix: str, defaults: dict | None = None):
    defaults = defaults or {}
    name = st.text_input("Name", value=defaults.get("name", ""), key=f"{prefix}_name")
    primary = st.multiselect(
        "Primary muscles", _MUSCLE_GROUPS, default=defaults.get("primary_muscles", []),
        key=f"{prefix}_primary",
    )
    secondary = st.multiselect(
        "Secondary muscles", _MUSCLE_GROUPS, default=defaults.get("secondary_muscles", []),
        key=f"{prefix}_secondary",
    )
    equip_index = _EQUIPMENT.index(defaults["equipment"]) if defaults.get("equipment") in _EQUIPMENT else 0
    diff_index = _DIFFICULTIES.index(defaults["difficulty"]) if defaults.get("difficulty") in _DIFFICULTIES else 0
    equipment = st.selectbox("Equipment", _EQUIPMENT, index=equip_index, key=f"{prefix}_equip")
    difficulty = st.selectbox("Difficulty", _DIFFICULTIES, index=diff_index, key=f"{prefix}_diff")
    return name, primary, secondary, equipment, difficulty


def _build_exercise_payload(name, primary, secondary, equipment, difficulty) -> dict | list[str]:
    errors = []
    if not name.strip():
        errors.append("Name is required.")
    if not primary:
        errors.append("Select at least one primary muscle.")
    overlap = set(primary) & set(secondary)
    if overlap:
        errors.append(f"Muscles cannot be both primary and secondary: {', '.join(sorted(overlap))}")
    if errors:
        return errors
    return {
        "name": name.strip(),
        "primary_muscles": primary,
        "secondary_muscles": secondary,
        "equipment": equipment,
        "difficulty": difficulty,
    }


def _admin_add_form(token: str) -> None:
    with st.form("admin_add"):
        fields = _exercise_form_fields("add")
        submitted = st.form_submit_button("Add exercise", type="primary")
    if not submitted:
        return
    result = _build_exercise_payload(*fields)
    if isinstance(result, list):
        for err in result:
            st.warning(err)
        return
    try:
        create_exercise(result, token=token)
        st.success(f'Added "{result["name"]}".')
        st.session_state["exercises"] = _load_exercises()
    except (BackendUnavailableError, ValueError) as exc:
        st.error(str(exc))


def _admin_edit_form(token: str, exercises: list[dict]) -> None:
    if not exercises:
        st.info("No exercises to edit yet.")
        return
    labels = {f'#{ex["id"]} · {ex["name"]}': ex for ex in exercises if "id" in ex}
    choice = st.selectbox("Select exercise", list(labels), key="edit_choice")
    target = labels[choice]
    with st.form("admin_edit"):
        fields = _exercise_form_fields("edit", target)
        submitted = st.form_submit_button("Save changes", type="primary")
    if not submitted:
        return
    result = _build_exercise_payload(*fields)
    if isinstance(result, list):
        for err in result:
            st.warning(err)
        return
    try:
        update_exercise(target["id"], result, token=token)
        st.success(f'Updated "{result["name"]}".')
        st.session_state["exercises"] = _load_exercises()
    except (BackendUnavailableError, ValueError) as exc:
        st.error(str(exc))


def _admin_delete_form(token: str, exercises: list[dict]) -> None:
    if not exercises:
        st.info("No exercises to delete.")
        return
    labels = {f'#{ex["id"]} · {ex["name"]}': ex for ex in exercises if "id" in ex}
    choice = st.selectbox("Select exercise", list(labels), key="delete_choice")
    if st.button("Delete exercise", type="primary"):
        try:
            delete_exercise(labels[choice]["id"], token=token)
            st.success("Exercise deleted.")
            st.session_state["exercises"] = _load_exercises()
            st.rerun()
        except (BackendUnavailableError, ValueError) as exc:
            st.error(str(exc))


# --------------------------------------------------------------------------- #
# Shell
# --------------------------------------------------------------------------- #
def _sidebar_nav(user: dict, provider: str) -> str:
    with st.sidebar:
        _md(
            f'<div class="tf-card" style="margin-bottom:14px">'
            f'<div class="tf-metric-label">Signed in</div>'
            f'<div style="font-weight:600;font-size:1.05rem">{user["username"]}</div>'
            f'<div style="margin-top:6px">{ui.badge(user.get("role", "athlete"), "status-ok")}'
            f'{ui.provider_badge(provider)}</div></div>'
        )
        pages = ["Dashboard", "AI Coach", "Exercise Catalog", "Workout History"]
        if is_admin(user):
            pages.append("Admin Catalog")
        # Keep the keyed nav state valid (e.g. after a role change/logout).
        if st.session_state.get("nav") not in pages:
            st.session_state["nav"] = "Dashboard"
        page = st.radio("Navigation", pages, key="nav", label_visibility="collapsed")
        st.divider()
        if st.button("Log out", width="stretch"):
            for key in ("token", "username", "user", "last_plan"):
                st.session_state.pop(key, None)
            st.rerun()
    return page


def main() -> None:
    st.set_page_config(page_title="TrainFlow", page_icon="⚡", layout="wide")
    _md(ui.styles())

    if "exercises" not in st.session_state:
        st.session_state["exercises"] = _load_exercises()

    user = st.session_state.get("user")
    if not st.session_state.get("token") or not user:
        _auth_screen()
        return

    provider = coach_status()
    page = _sidebar_nav(user, provider)

    meta = ui.badge(f"{user['username']} · {user.get('role', 'athlete')}", "status-ok") + ui.provider_badge(provider)
    _md(ui.hero("TrainFlow Coach", _TAGLINE, meta))
    st.write("")

    if page == "Dashboard":
        _page_dashboard(user, provider)
    elif page == "AI Coach":
        _page_coach(user, provider)
    elif page == "Exercise Catalog":
        _page_catalog()
    elif page == "Workout History":
        _page_history(user)
    elif page == "Admin Catalog" and is_admin(user):
        _page_admin()


if __name__ == "__main__":
    main()
