from datetime import date, timedelta

from sqlmodel import Session, select

from app.auth import ALL_SCOPES, ATHLETE_SCOPES, hash_password
from app.models import ExerciseTable, UserTable, WorkoutExercise, WorkoutSession

# Re-exported for callers/tests that import scope lists from app.seed.
__all__ = ["ALL_SCOPES", "ATHLETE_SCOPES", "seed_all", "seed_users", "seed_exercises", "seed_sessions"]

_DEMO_USERS = [
    {
        "username": "admin",
        "password": "admin123",
        "role": "admin",
        "scopes": ALL_SCOPES,
    },
    {
        "username": "athlete",
        "password": "athlete123",
        "role": "athlete",
        "scopes": ATHLETE_SCOPES,
    },
]

_DEMO_EXERCISES = [
    {
        "name": "Barbell Bench Press",
        "primary_muscles": ["chest"],
        "secondary_muscles": ["triceps", "shoulders"],
        "equipment": "barbell",
        "difficulty": "intermediate",
    },
    {
        "name": "Push Up",
        "primary_muscles": ["chest"],
        "secondary_muscles": ["triceps", "shoulders"],
        "equipment": "bodyweight",
        "difficulty": "beginner",
    },
    {
        "name": "Incline Dumbbell Press",
        "primary_muscles": ["chest"],
        "secondary_muscles": ["shoulders", "triceps"],
        "equipment": "dumbbell",
        "difficulty": "intermediate",
    },
    {
        "name": "Pull Up",
        "primary_muscles": ["back"],
        "secondary_muscles": ["biceps"],
        "equipment": "bodyweight",
        "difficulty": "intermediate",
    },
    {
        "name": "Bent Over Barbell Row",
        "primary_muscles": ["back"],
        "secondary_muscles": ["biceps", "forearms"],
        "equipment": "barbell",
        "difficulty": "intermediate",
    },
    {
        "name": "Lat Pulldown",
        "primary_muscles": ["back"],
        "secondary_muscles": ["biceps"],
        "equipment": "cable",
        "difficulty": "beginner",
    },
    {
        "name": "Overhead Press",
        "primary_muscles": ["shoulders"],
        "secondary_muscles": ["triceps"],
        "equipment": "barbell",
        "difficulty": "intermediate",
    },
    {
        "name": "Dumbbell Lateral Raise",
        "primary_muscles": ["shoulders"],
        "secondary_muscles": [],
        "equipment": "dumbbell",
        "difficulty": "beginner",
    },
    {
        "name": "Barbell Back Squat",
        "primary_muscles": ["quadriceps"],
        "secondary_muscles": ["glutes", "hamstrings"],
        "equipment": "barbell",
        "difficulty": "intermediate",
    },
    {
        "name": "Romanian Deadlift",
        "primary_muscles": ["hamstrings"],
        "secondary_muscles": ["glutes", "back"],
        "equipment": "barbell",
        "difficulty": "intermediate",
    },
    {
        "name": "Walking Lunge",
        "primary_muscles": ["quadriceps"],
        "secondary_muscles": ["glutes", "hamstrings"],
        "equipment": "dumbbell",
        "difficulty": "beginner",
    },
    {
        "name": "Standing Calf Raise",
        "primary_muscles": ["calves"],
        "secondary_muscles": [],
        "equipment": "machine",
        "difficulty": "beginner",
    },
    {
        "name": "Barbell Biceps Curl",
        "primary_muscles": ["biceps"],
        "secondary_muscles": ["forearms"],
        "equipment": "barbell",
        "difficulty": "beginner",
    },
    {
        "name": "Triceps Pushdown",
        "primary_muscles": ["triceps"],
        "secondary_muscles": [],
        "equipment": "cable",
        "difficulty": "beginner",
    },
    {
        "name": "Plank",
        "primary_muscles": ["core"],
        "secondary_muscles": [],
        "equipment": "bodyweight",
        "difficulty": "beginner",
    },
    {
        "name": "Hanging Leg Raise",
        "primary_muscles": ["core"],
        "secondary_muscles": ["forearms"],
        "equipment": "bodyweight",
        "difficulty": "intermediate",
    },
]


def seed_users(session: Session) -> None:
    if session.exec(select(UserTable)).first() is not None:
        return
    for spec in _DEMO_USERS:
        session.add(
            UserTable(
                username=spec["username"],
                hashed_password=hash_password(spec["password"]),
                role=spec["role"],
                scopes=spec["scopes"],
            )
        )
    session.commit()


def seed_exercises(session: Session) -> None:
    if session.exec(select(ExerciseTable)).first() is not None:
        return
    for spec in _DEMO_EXERCISES:
        session.add(
            ExerciseTable(
                name=spec["name"],
                primary_muscles=spec["primary_muscles"],
                secondary_muscles=spec["secondary_muscles"],
                equipment=spec["equipment"],
                difficulty=spec["difficulty"],
                instructions=spec.get("instructions"),
                media_url=spec.get("media_url"),
            )
        )
    session.commit()


# Two recent chest/push-focused sessions so the Coach has history to reason
# about (e.g. "recent sessions were chest-heavy -> add back volume").
_DEMO_SESSIONS = [
    {
        "days_ago": 2,
        "goal": "hypertrophy",
        "notes": "Heavy chest day",
        "exercises": [
            ("Barbell Bench Press", 4, 8, 60.0),
            ("Incline Dumbbell Press", 3, 10, 24.0),
            ("Push Up", 3, 15, None),
            ("Triceps Pushdown", 3, 12, 25.0),
        ],
    },
    {
        "days_ago": 4,
        "goal": "hypertrophy",
        "notes": "Push session",
        "exercises": [
            ("Overhead Press", 4, 8, 40.0),
            ("Dumbbell Lateral Raise", 3, 15, 8.0),
            ("Barbell Bench Press", 3, 10, 55.0),
        ],
    },
]


def seed_sessions(session: Session) -> None:
    if session.exec(select(WorkoutSession)).first() is not None:
        return

    def exercise_id(name: str) -> int | None:
        row = session.exec(select(ExerciseTable).where(ExerciseTable.name == name)).first()
        return row.id if row is not None else None

    today = date.today()
    for spec in _DEMO_SESSIONS:
        workout = WorkoutSession(
            owner="athlete",
            date=today - timedelta(days=spec["days_ago"]),
            goal=spec["goal"],
            notes=spec["notes"],
        )
        session.add(workout)
        session.flush()
        for name, sets, reps, weight in spec["exercises"]:
            eid = exercise_id(name)
            if eid is not None:
                session.add(
                    WorkoutExercise(
                        session_id=workout.id,
                        exercise_id=eid,
                        sets=sets,
                        reps=reps,
                        weight=weight,
                    )
                )
    session.commit()


def seed_all(session: Session) -> None:
    seed_users(session)
    seed_exercises(session)
    seed_sessions(session)
