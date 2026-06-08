import datetime as dt

import pandas as pd
import streamlit as st

from client import (
    BackendUnavailableError,
    create_exercise,
    get_me,
    list_exercises,
    list_sessions,
    log_session,
    login,
    register,
    request_plan,
)
from coach import EXPERIENCES, GOALS, build_plan_payload, plan_day_rows, resolve_avoid_ids
from export import generate_reference_sheet
from filters import apply_filters
from permissions import can_manage_catalog, history_scope_label, is_admin

_MUSCLE_GROUPS = [
    "chest", "back", "shoulders", "biceps", "triceps",
    "core", "glutes", "calves", "forearms", "quadriceps", "hamstrings",
]
_EQUIPMENT = ["bodyweight", "dumbbell", "barbell", "machine", "cable", "smith"]
_DIFFICULTIES = ["beginner", "intermediate", "advanced"]

_BACKEND_HINT = (
    "Cannot reach the backend. Start it first:\n\n"
    "`cd services/exercise-service && uv run uvicorn app.main:app --reload`"
)


def _load_exercises() -> list[dict] | None:
    try:
        return list_exercises()
    except BackendUnavailableError:
        return None


def _sign_in(token: str, username: str) -> None:
    st.session_state["token"] = token
    st.session_state["username"] = username
    try:
        st.session_state["user"] = get_me(token)
    except BackendUnavailableError:
        st.session_state["user"] = {"username": username, "role": "athlete", "scopes": []}


def _login_form() -> None:
    with st.form("login_form"):
        st.caption("Demo admin: admin / admin123")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in")
    if submitted:
        try:
            token = login(username, password)
            _sign_in(token, username)
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
        submitted = st.form_submit_button("Create account")
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
        # Auto-log-in after a successful registration.
        token = login(username.strip(), password)
        _sign_in(token, username.strip())
        st.success("Account created — you are now signed in.")
        st.rerun()
    except ValueError as exc:
        st.error(f"Registration failed: {exc}")
    except BackendUnavailableError:
        st.error("Cannot reach the backend.")


def _auth_sidebar() -> None:
    st.header("Account")
    user = st.session_state.get("user")
    if st.session_state.get("token") and user:
        st.success(f"Signed in as {user['username']} ({user.get('role', 'athlete')})")
        if st.button("Log out"):
            for key in ("token", "username", "user"):
                st.session_state.pop(key, None)
            st.rerun()
        return

    mode = st.radio("", ["Log in", "Register"], horizontal=True, label_visibility="collapsed")
    if mode == "Log in":
        _login_form()
    else:
        _register_form()


def _browse_tab(exercises: list[dict] | None, filters: dict) -> None:
    if exercises is None:
        st.error(_BACKEND_HINT)
        return

    filtered = apply_filters(
        exercises,
        filters["muscles"],
        filters["equipment"],
        filters["difficulties"],
    )
    st.caption(f"{len(filtered)} exercise(s) shown")

    if filtered:
        df = pd.DataFrame(
            [
                {
                    "Name": ex["name"],
                    "Primary Muscles": ", ".join(ex["primary_muscles"]),
                    "Secondary Muscles": ", ".join(ex.get("secondary_muscles", [])),
                    "Equipment": ex["equipment"],
                    "Difficulty": ex["difficulty"],
                }
                for ex in filtered
            ]
        )
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No exercises match the selected filters.")

    png_bytes = generate_reference_sheet(filtered)
    st.download_button(
        label="Export PNG",
        data=png_bytes,
        file_name="workout_reference.png",
        mime="image/png",
        disabled=len(filtered) == 0,
    )


def _add_tab() -> None:
    # Only rendered for admins, but re-check server-authoritative scope anyway.
    token = st.session_state.get("token")
    with st.form("add_exercise_form"):
        name = st.text_input("Name")
        primary_muscles = st.multiselect("Primary Muscles", _MUSCLE_GROUPS)
        secondary_muscles = st.multiselect("Secondary Muscles", _MUSCLE_GROUPS)
        equipment = st.selectbox("Equipment", _EQUIPMENT)
        difficulty = st.selectbox("Difficulty", _DIFFICULTIES)
        instructions = st.text_area("Instructions (optional)")
        media_url = st.text_input("Media URL (optional)")
        submitted = st.form_submit_button("Add Exercise")

    if not submitted:
        return

    errors = []
    if not name.strip():
        errors.append("Name is required.")
    if not primary_muscles:
        errors.append("Select at least one primary muscle.")
    overlap = set(primary_muscles) & set(secondary_muscles)
    if overlap:
        errors.append(f"Muscles cannot be both primary and secondary: {', '.join(sorted(overlap))}")
    if media_url.strip() and not media_url.strip().startswith(("http://", "https://")):
        errors.append("Media URL must start with http:// or https://")

    if errors:
        for err in errors:
            st.warning(err)
        return

    payload: dict = {
        "name": name.strip(),
        "primary_muscles": primary_muscles,
        "secondary_muscles": secondary_muscles,
        "equipment": equipment,
        "difficulty": difficulty,
    }
    if instructions.strip():
        payload["instructions"] = instructions.strip()
    if media_url.strip():
        payload["media_url"] = media_url.strip()

    try:
        create_exercise(payload, token=token)
        st.success(f'Exercise "{name.strip()}" added successfully.')
        st.session_state["exercises"] = _load_exercises()
    except BackendUnavailableError:
        st.error("Cannot reach the backend. Is the API running on port 8000?")
    except ValueError as exc:
        st.error(f"Validation error: {exc}")


def _history_tab(exercises: list[dict] | None) -> None:
    token = st.session_state.get("token")
    user = st.session_state.get("user")
    if not token:
        st.info("Log in to view and log workout history.")
        return

    st.caption(f"Showing {history_scope_label(user)}.")
    catalog = exercises or []
    by_id = {ex["id"]: ex for ex in catalog if "id" in ex}

    try:
        sessions = list_sessions(token, limit=20)
    except BackendUnavailableError:
        st.error("Cannot reach the backend.")
        return

    if sessions:
        for s in sessions:
            owner = f" · {s.get('owner')}" if is_admin(user) and s.get("owner") else ""
            with st.expander(f"{s['date']} — {s['goal']}{owner}"):
                rows = [
                    {
                        "Exercise": by_id.get(i["exercise_id"], {}).get(
                            "name", i.get("exercise_name", f"#{i['exercise_id']}")
                        ),
                        "Sets": i["sets"],
                        "Reps": i["reps"],
                        "Weight": i.get("weight"),
                    }
                    for i in s["exercises"]
                ]
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No workout history yet. Log your first session below.")

    st.divider()
    st.subheader("Log a session")
    with st.form("log_session_form"):
        date = st.date_input("Date", value=dt.date.today())
        goal = st.selectbox("Goal", GOALS, index=1)
        names = st.multiselect("Exercises", [ex["name"] for ex in catalog])
        col1, col2, col3 = st.columns(3)
        with col1:
            sets = st.number_input("Sets", min_value=1, max_value=10, value=3)
        with col2:
            reps = st.number_input("Reps", min_value=1, max_value=100, value=10)
        with col3:
            weight = st.number_input("Weight (kg, 0 = bodyweight)", min_value=0.0, value=0.0)
        submitted = st.form_submit_button("Log session")

    if not submitted:
        return
    name_to_id = {ex["name"]: ex["id"] for ex in catalog if "id" in ex}
    chosen_ids = [name_to_id[n] for n in names if n in name_to_id]
    if not chosen_ids:
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
            for eid in chosen_ids
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


def _coach_tab(exercises: list[dict] | None) -> None:
    token = st.session_state.get("token")
    if not token:
        st.info("Log in (or register) to generate a personalized workout plan.")
        return

    catalog = exercises or []
    with st.form("coach_form"):
        col1, col2 = st.columns(2)
        with col1:
            goal = st.selectbox("Goal", GOALS, index=1)
            days_per_week = st.slider("Days per week", 1, 7, 3)
        with col2:
            experience = st.selectbox("Experience", EXPERIENCES, index=1)
            session_minutes = st.slider("Session length (minutes)", 15, 120, 60, step=5)
        available_equipment = st.multiselect("Available equipment", _EQUIPMENT)
        target_muscles = st.multiselect("Emphasize muscles (optional)", _MUSCLE_GROUPS)
        avoid_names = st.multiselect(
            "Avoid exercises (optional)", [ex["name"] for ex in catalog]
        )
        submitted = st.form_submit_button("Generate plan")

    if not submitted:
        return

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
        plan = request_plan(payload, token)
    except BackendUnavailableError:
        st.error("Cannot reach the coach service. Is it running on port 8001?")
        return
    except ValueError as exc:
        st.error(f"Coach error: {exc}")
        return

    badge = "🤖 LLM" if plan.get("generated_by") == "llm" else "⚙️ Fallback"
    st.caption(f"Plan generated by: {badge}")
    for insight in plan.get("insights", []):
        st.info(insight)

    for index, day in enumerate(plan.get("days", []), start=1):
        st.subheader(f"Day {index} — {day.get('focus', 'Workout')}")
        rows = plan_day_rows(day)
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    if plan.get("notes"):
        st.caption(plan["notes"])


def main() -> None:
    st.set_page_config(page_title="TrainFlow", layout="wide")
    st.title("TrainFlow — Coach")

    if "exercises" not in st.session_state:
        st.session_state["exercises"] = _load_exercises()

    user = st.session_state.get("user")

    with st.sidebar:
        _auth_sidebar()
        st.divider()
        st.header("Filters")
        selected_muscles = st.multiselect("Muscle Group", _MUSCLE_GROUPS)
        selected_equipment = st.multiselect("Equipment", _EQUIPMENT)
        selected_difficulties = st.multiselect("Difficulty", _DIFFICULTIES)
        if st.button("Refresh"):
            st.session_state["exercises"] = _load_exercises()

    filters = {
        "muscles": selected_muscles,
        "equipment": selected_equipment,
        "difficulties": selected_difficulties,
    }

    # Catalog management is admin-only; athletes never see the tab.
    tab_labels = ["Browse Exercises", "Coach", "History"]
    if can_manage_catalog(user):
        tab_labels.insert(1, "Add Exercise")
    tabs = dict(zip(tab_labels, st.tabs(tab_labels)))

    with tabs["Browse Exercises"]:
        _browse_tab(st.session_state["exercises"], filters)
    if "Add Exercise" in tabs:
        with tabs["Add Exercise"]:
            _add_tab()
    with tabs["Coach"]:
        _coach_tab(st.session_state["exercises"])
    with tabs["History"]:
        _history_tab(st.session_state["exercises"])


if __name__ == "__main__":
    main()
