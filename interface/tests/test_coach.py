from coach import build_plan_payload, plan_day_rows, resolve_avoid_ids

_CATALOG = [
    {"id": 1, "name": "Barbell Bench Press"},
    {"id": 2, "name": "Pull Up"},
    {"id": 3, "name": "Back Squat"},
]


def test_resolve_avoid_ids_maps_names():
    assert resolve_avoid_ids(["Pull Up", "Back Squat"], _CATALOG) == [2, 3]


def test_resolve_avoid_ids_ignores_unknown_names():
    assert resolve_avoid_ids(["Pull Up", "Nonexistent"], _CATALOG) == [2]


def test_build_plan_payload_shape_and_coercion():
    payload = build_plan_payload(
        goal="hypertrophy",
        experience="intermediate",
        days_per_week="3",
        session_minutes="60",
        available_equipment=["barbell"],
        target_muscles=["back"],
        avoid_exercise_ids=[1],
    )
    assert payload == {
        "goal": "hypertrophy",
        "experience": "intermediate",
        "days_per_week": 3,
        "session_minutes": 60,
        "available_equipment": ["barbell"],
        "target_muscles": ["back"],
        "avoid_exercise_ids": [1],
        "history_limit": 5,
    }


def test_plan_day_rows_flattens_items():
    day = {
        "focus": "Push",
        "items": [
            {"exercise_id": 1, "exercise_name": "Bench", "sets": 4, "reps": "8-12",
             "rest_seconds": 90, "rationale": "main lift"},
            {"exercise_id": 2, "exercise_name": "Dip", "sets": 3, "reps": "10",
             "rest_seconds": 60, "rationale": None},
        ],
    }
    rows = plan_day_rows(day)
    assert rows[0] == {
        "Exercise": "Bench", "Sets": 4, "Reps": "8-12", "Rest (s)": 90, "Why": "main lift",
    }
    # Missing rationale renders as an empty string, not None.
    assert rows[1]["Why"] == ""


def test_plan_day_rows_falls_back_to_id_when_name_missing():
    rows = plan_day_rows({"items": [{"exercise_id": 7, "sets": 3, "reps": "5", "rest_seconds": 120}]})
    assert rows[0]["Exercise"] == "#7"
