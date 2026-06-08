"""Pure dashboard metric computation (no Streamlit), so it can be unit-tested."""

from collections import Counter


def compute_dashboard_metrics(exercises: list[dict] | None, sessions: list[dict] | None) -> dict:
    exercises = exercises or []
    sessions = sessions or []
    by_id = {ex["id"]: ex for ex in exercises if "id" in ex}
    equipment = {ex.get("equipment") for ex in exercises if ex.get("equipment")}

    focus = Counter()
    for session in sessions:
        for item in session.get("exercises", []):
            exercise = by_id.get(item.get("exercise_id"))
            if exercise:
                for muscle in exercise.get("primary_muscles", []):
                    focus[muscle] += 1

    return {
        "total_exercises": len(exercises),
        "total_sessions": len(sessions),
        "equipment_types": len(equipment),
        "top_focus": [muscle for muscle, _ in focus.most_common(3)],
    }
