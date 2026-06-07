import pytest

from app.schemas import CatalogExercise


@pytest.fixture
def catalog() -> list[CatalogExercise]:
    return [
        CatalogExercise(id=1, name="Barbell Bench Press", primary_muscles=["chest"],
                        secondary_muscles=["triceps"], equipment="barbell", difficulty="intermediate"),
        CatalogExercise(id=2, name="Incline Dumbbell Press", primary_muscles=["chest"],
                        secondary_muscles=["shoulders"], equipment="dumbbell", difficulty="intermediate"),
        CatalogExercise(id=3, name="Pull Up", primary_muscles=["back"],
                        secondary_muscles=["biceps"], equipment="bodyweight", difficulty="intermediate"),
        CatalogExercise(id=4, name="Bent Over Row", primary_muscles=["back"],
                        secondary_muscles=["biceps"], equipment="barbell", difficulty="intermediate"),
        CatalogExercise(id=5, name="Back Squat", primary_muscles=["quadriceps"],
                        secondary_muscles=["glutes"], equipment="barbell", difficulty="intermediate"),
        CatalogExercise(id=6, name="Overhead Press", primary_muscles=["shoulders"],
                        secondary_muscles=["triceps"], equipment="barbell", difficulty="intermediate"),
    ]


@pytest.fixture
def chest_heavy_history() -> list[dict]:
    # Newest-first, as exercise-service returns it.
    return [
        {
            "id": 2,
            "date": "2026-06-05",
            "goal": "hypertrophy",
            "exercises": [
                {"exercise_id": 1, "sets": 5, "reps": 8},
                {"exercise_id": 2, "sets": 4, "reps": 10},
            ],
        },
        {
            "id": 1,
            "date": "2026-06-03",
            "goal": "hypertrophy",
            "exercises": [
                {"exercise_id": 1, "sets": 4, "reps": 8},
            ],
        },
    ]
