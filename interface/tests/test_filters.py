import pytest

from filters import apply_filters

_EXERCISES = [
    {
        "name": "Push Up",
        "primary_muscles": ["chest", "triceps"],
        "equipment": "bodyweight",
        "difficulty": "beginner",
    },
    {
        "name": "Squat",
        "primary_muscles": ["quadriceps"],
        "secondary_muscles": ["glutes"],
        "equipment": "barbell",
        "difficulty": "beginner",
    },
    {
        "name": "Deadlift",
        "primary_muscles": ["back", "hamstrings"],
        "equipment": "barbell",
        "difficulty": "advanced",
    },
    {
        "name": "Cable Row",
        "primary_muscles": ["back"],
        "equipment": "cable",
        "difficulty": "intermediate",
    },
]


def test_no_filters_returns_all():
    assert apply_filters(_EXERCISES, [], [], []) == _EXERCISES


def test_filter_by_single_muscle():
    result = apply_filters(_EXERCISES, ["back"], [], [])
    names = [e["name"] for e in result]
    assert names == ["Deadlift", "Cable Row"]


def test_filter_by_multiple_muscles_uses_or_logic():
    result = apply_filters(_EXERCISES, ["chest", "quadriceps"], [], [])
    names = [e["name"] for e in result]
    assert set(names) == {"Push Up", "Squat"}


def test_filter_by_equipment():
    result = apply_filters(_EXERCISES, [], ["barbell"], [])
    names = [e["name"] for e in result]
    assert set(names) == {"Squat", "Deadlift"}


def test_filter_by_difficulty():
    result = apply_filters(_EXERCISES, [], [], ["beginner"])
    names = [e["name"] for e in result]
    assert set(names) == {"Push Up", "Squat"}


def test_filter_by_multiple_difficulties():
    result = apply_filters(_EXERCISES, [], [], ["beginner", "advanced"])
    names = [e["name"] for e in result]
    assert set(names) == {"Push Up", "Squat", "Deadlift"}


def test_filter_combining_muscle_and_equipment():
    result = apply_filters(_EXERCISES, ["back"], ["barbell"], [])
    assert len(result) == 1
    assert result[0]["name"] == "Deadlift"


def test_filter_combining_all_dimensions():
    result = apply_filters(_EXERCISES, ["back"], ["barbell"], ["advanced"])
    assert len(result) == 1
    assert result[0]["name"] == "Deadlift"


def test_filter_with_no_match_returns_empty():
    result = apply_filters(_EXERCISES, ["biceps"], [], [])
    assert result == []


def test_filter_on_empty_exercise_list():
    result = apply_filters([], ["chest"], ["barbell"], ["beginner"])
    assert result == []


def test_muscle_filter_matches_primary_muscles_only():
    # "glutes" is only in secondary_muscles of Squat — should not match
    result = apply_filters(_EXERCISES, ["glutes"], [], [])
    assert result == []
