import pandas as pd
import streamlit as st

from client import (
    BackendUnavailableError,
    create_exercise,
    list_exercises,
    login,
    request_plan,
)
from coach import EXPERIENCES, GOALS, build_plan_payload, plan_day_rows, resolve_avoid_ids
from export import generate_reference_sheet
from filters import apply_filters

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


def _login_sidebar() -> None:
    st.header("Account")
    token = st.session_state.get("token")
    if token:
        st.success(f"Signed in as {st.session_state.get('username', 'user')}")
        if st.button("Log out"):
            st.session_state.pop("token", None)
            st.session_state.pop("username", None)
            st.rerun()
        return

    with st.form("login_form"):
        st.caption("Demo users: admin / admin123 · athlete / athlete123")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in")
    if submitted:
        try:
            st.session_state["token"] = login(username, password)
            st.session_state["username"] = username
            st.rerun()
        except ValueError:
            st.error("Incorrect username or password.")
        except BackendUnavailableError:
            st.error("Cannot reach the backend.")


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
    token = st.session_state.get("token")
    if not token:
        st.info("Log in as a writer (e.g. admin) to add exercises.")
        return

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


def _coach_tab(exercises: list[dict] | None) -> None:
    token = st.session_state.get("token")
    if not token:
        st.info("Log in (e.g. athlete) to generate a personalized workout plan.")
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

    with st.sidebar:
        _login_sidebar()
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

    browse_tab, add_tab, coach_tab = st.tabs(
        ["Browse Exercises", "Add Exercise", "Coach"]
    )
    with browse_tab:
        _browse_tab(st.session_state["exercises"], filters)
    with add_tab:
        _add_tab()
    with coach_tab:
        _coach_tab(st.session_state["exercises"])


if __name__ == "__main__":
    main()
