"""Pure helpers for the Coach tab — building the plan request payload and
shaping the response for display. Kept free of Streamlit and HTTP so they can be
unit-tested directly.
"""

import re

GOALS = ["strength", "hypertrophy", "endurance", "general"]
EXPERIENCES = ["beginner", "intermediate", "advanced"]


def resolve_avoid_ids(selected_names: list[str], exercises: list[dict]) -> list[int]:
    """Map exercise names chosen in the UI to their catalog ids."""
    by_name = {ex["name"]: ex["id"] for ex in exercises if "id" in ex}
    return [by_name[name] for name in selected_names if name in by_name]


def build_plan_payload(
    *,
    goal: str,
    experience: str,
    days_per_week: int,
    session_minutes: int,
    available_equipment: list[str],
    target_muscles: list[str],
    avoid_exercise_ids: list[int],
    history_limit: int = 5,
) -> dict:
    return {
        "goal": goal,
        "experience": experience,
        "days_per_week": int(days_per_week),
        "session_minutes": int(session_minutes),
        "available_equipment": list(available_equipment),
        "target_muscles": list(target_muscles),
        "avoid_exercise_ids": list(avoid_exercise_ids),
        "history_limit": int(history_limit),
    }


def plan_record_payload(plan: dict, request: dict | None = None) -> dict:
    """Build the body for persisting a generated plan (exercise-service POST /plans)."""
    return {
        "goal": plan.get("goal", "general"),
        "generated_by": plan.get("generated_by", "fallback"),
        "request": request or {},
        "plan": plan,
    }


def first_int(value, default: int = 10) -> int:
    """Parse the first integer from a reps string like '8-12' or 'AMRAP'."""
    match = re.search(r"\d+", str(value))
    return int(match.group()) if match else default


def plan_day_to_session(day: dict, goal: str, date_iso: str) -> dict:
    """Convert a plan day into a loggable workout-session payload."""
    return {
        "date": date_iso,
        "goal": goal,
        "exercises": [
            {
                "exercise_id": item["exercise_id"],
                "sets": max(1, min(10, int(item.get("sets", 3)))),
                "reps": max(1, min(100, first_int(item.get("reps")))),
                "weight": None,
            }
            for item in day.get("items", [])
        ],
    }


def plan_day_rows(day: dict) -> list[dict]:
    """Flatten a plan day's items into rows for a dataframe."""
    rows = []
    for item in day.get("items", []):
        rows.append(
            {
                "Exercise": item.get("exercise_name", f"#{item.get('exercise_id')}"),
                "Sets": item.get("sets"),
                "Reps": item.get("reps"),
                "Rest (s)": item.get("rest_seconds"),
                "Why": item.get("rationale") or "",
            }
        )
    return rows
