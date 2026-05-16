import pytest

from export import generate_reference_sheet

_PNG_MAGIC = b"\x89PNG"

_EXERCISES = [
    {
        "name": "Push Up",
        "primary_muscles": ["chest"],
        "secondary_muscles": ["triceps"],
        "equipment": "bodyweight",
        "difficulty": "beginner",
    },
    {
        "name": "Squat",
        "primary_muscles": ["quadriceps"],
        "secondary_muscles": ["glutes", "hamstrings"],
        "equipment": "barbell",
        "difficulty": "beginner",
    },
]


def test_returns_bytes():
    result = generate_reference_sheet(_EXERCISES)
    assert isinstance(result, bytes)


def test_output_is_valid_png():
    result = generate_reference_sheet(_EXERCISES)
    assert result[:4] == _PNG_MAGIC


def test_empty_list_returns_valid_png():
    result = generate_reference_sheet([])
    assert result[:4] == _PNG_MAGIC


def test_single_exercise_returns_valid_png():
    result = generate_reference_sheet(_EXERCISES[:1])
    assert result[:4] == _PNG_MAGIC


def test_long_name_does_not_crash():
    long_name_exercise = {**_EXERCISES[0], "name": "A" * 100}
    result = generate_reference_sheet([long_name_exercise])
    assert result[:4] == _PNG_MAGIC


def test_many_exercises_returns_valid_png():
    many = _EXERCISES * 20
    result = generate_reference_sheet(many)
    assert result[:4] == _PNG_MAGIC


def test_output_is_non_empty():
    result = generate_reference_sheet(_EXERCISES)
    assert len(result) > 1000
