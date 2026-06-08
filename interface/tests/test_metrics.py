from metrics import compute_dashboard_metrics

_CATALOG = [
    {"id": 1, "name": "Bench", "primary_muscles": ["chest"], "equipment": "barbell"},
    {"id": 2, "name": "Row", "primary_muscles": ["back"], "equipment": "barbell"},
    {"id": 3, "name": "Pushup", "primary_muscles": ["chest"], "equipment": "bodyweight"},
]
_SESSIONS = [
    {"date": "2026-06-05", "exercises": [{"exercise_id": 1, "sets": 4}, {"exercise_id": 3, "sets": 3}]},
    {"date": "2026-06-03", "exercises": [{"exercise_id": 1, "sets": 5}]},
]


def test_counts():
    m = compute_dashboard_metrics(_CATALOG, _SESSIONS)
    assert m["total_exercises"] == 3
    assert m["total_sessions"] == 2
    assert m["equipment_types"] == 2  # barbell, bodyweight


def test_top_focus_orders_by_frequency():
    m = compute_dashboard_metrics(_CATALOG, _SESSIONS)
    # chest appears in 3 logged exercises, back in 0 -> chest leads
    assert m["top_focus"][0] == "chest"


def test_focus_total_counts_distinct_muscles():
    m = compute_dashboard_metrics(_CATALOG, _SESSIONS)
    assert m["focus_total"] == 1  # only chest was trained


def test_empty_inputs_are_safe():
    m = compute_dashboard_metrics(None, None)
    assert m == {
        "total_exercises": 0,
        "total_sessions": 0,
        "equipment_types": 0,
        "top_focus": [],
        "focus_total": 0,
    }
