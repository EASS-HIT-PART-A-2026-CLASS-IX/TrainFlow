from export import generate_plan_sheet

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

_PLAN = {
    "goal": "hypertrophy",
    "generated_by": "gemini",
    "days_per_week": 2,
    "insights": ["You trained chest heavily recently."],
    "notes": "Keep one rest day between sessions.",
    "days": [
        {"focus": "Push", "items": [
            {"exercise_id": 1, "exercise_name": "Bench Press", "sets": 4,
             "reps": "8-12", "rest_seconds": 90, "rationale": "primary chest movement"},
        ]},
        {"focus": "Pull", "items": [
            {"exercise_id": 3, "exercise_name": "Pull Up", "sets": 3,
             "reps": "6-8", "rest_seconds": 120},
        ]},
    ],
}


def test_generate_plan_sheet_returns_png_bytes():
    data = generate_plan_sheet(_PLAN)
    assert isinstance(data, bytes) and len(data) > 1000
    assert data.startswith(_PNG_MAGIC)


def test_generate_plan_sheet_handles_empty_plan():
    data = generate_plan_sheet({})
    assert data.startswith(_PNG_MAGIC)
