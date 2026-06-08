from datetime import date
from enum import Enum

from pydantic import AnyUrl, BaseModel, Field, field_validator, model_validator
from sqlalchemy import Column, JSON
from sqlmodel import Field as SQLField
from sqlmodel import SQLModel


class MuscleGroup(str, Enum):
    chest = "chest"
    back = "back"
    shoulders = "shoulders"
    biceps = "biceps"
    triceps = "triceps"
    core = "core"
    glutes = "glutes"
    calves = "calves"
    forearms = "forearms"
    quadriceps = "quadriceps"
    hamstrings = "hamstrings"


class Equipment(str, Enum):
    bodyweight = "bodyweight"
    dumbbell = "dumbbell"
    barbell = "barbell"
    machine = "machine"
    cable = "cable"
    smith = "smith"


class Difficulty(str, Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class Goal(str, Enum):
    strength = "strength"
    hypertrophy = "hypertrophy"
    endurance = "endurance"
    general = "general"


# ---------------------------------------------------------------------------
# API schemas (Pydantic) — validation lives here and is the public contract.
# ---------------------------------------------------------------------------
class ExerciseBase(BaseModel):
    name: str
    primary_muscles: list[MuscleGroup] = Field(min_length=1)
    secondary_muscles: list[MuscleGroup] = Field(default_factory=list)
    equipment: Equipment
    difficulty: Difficulty
    instructions: str | None = None
    media_url: AnyUrl | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("name cannot be empty or whitespace-only")
        return value.strip()

    @model_validator(mode="after")
    def validate_muscle_overlap(self) -> "ExerciseBase":
        overlap = set(self.primary_muscles) & set(self.secondary_muscles)
        if overlap:
            raise ValueError("muscles cannot appear in both primary_muscles and secondary_muscles")
        return self


class ExerciseInput(ExerciseBase):
    pass


class Exercise(ExerciseBase):
    id: int


# ---------------------------------------------------------------------------
# Persistence tables (SQLModel).
# ---------------------------------------------------------------------------
class ExerciseTable(SQLModel, table=True):
    __tablename__ = "exercise"

    id: int | None = SQLField(default=None, primary_key=True)
    name: str = SQLField(index=True)
    primary_muscles: list[str] = SQLField(sa_column=Column(JSON))
    secondary_muscles: list[str] = SQLField(sa_column=Column(JSON))
    equipment: str
    difficulty: str
    instructions: str | None = None
    media_url: str | None = None


class UserTable(SQLModel, table=True):
    __tablename__ = "user"

    id: int | None = SQLField(default=None, primary_key=True)
    username: str = SQLField(index=True, unique=True)
    hashed_password: str
    role: str
    scopes: list[str] = SQLField(sa_column=Column(JSON))


class WorkoutSession(SQLModel, table=True):
    __tablename__ = "workoutsession"

    id: int | None = SQLField(default=None, primary_key=True)
    owner: str | None = SQLField(default=None, index=True)
    date: date
    goal: str
    notes: str | None = None


class WorkoutExercise(SQLModel, table=True):
    __tablename__ = "workoutexercise"

    id: int | None = SQLField(default=None, primary_key=True)
    session_id: int = SQLField(foreign_key="workoutsession.id", index=True)
    exercise_id: int = SQLField(foreign_key="exercise.id")
    sets: int
    reps: int
    weight: float | None = None


# ---------------------------------------------------------------------------
# Workout history API schemas. Kept intentionally lightweight.
# ---------------------------------------------------------------------------
class WorkoutExerciseInput(BaseModel):
    exercise_id: int
    sets: int = Field(ge=1, le=10)
    reps: int = Field(ge=1, le=100)
    weight: float | None = Field(default=None, ge=0)


class WorkoutExerciseRead(WorkoutExerciseInput):
    id: int
    exercise_name: str | None = None


class WorkoutSessionInput(BaseModel):
    date: date
    goal: Goal
    notes: str | None = None
    exercises: list[WorkoutExerciseInput] = Field(min_length=1)


class WorkoutSessionRead(BaseModel):
    id: int
    owner: str | None = None
    date: date
    goal: Goal
    notes: str | None = None
    exercises: list[WorkoutExerciseRead]


# ---------------------------------------------------------------------------
# Auth schemas.
# ---------------------------------------------------------------------------
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    scopes: list[str] = Field(default_factory=list)


class UserRegister(BaseModel):
    # Only username + password are accepted. Role/scopes are NOT client-settable;
    # registrations are always athletes (see auth_routes).
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("username cannot be empty")
        return cleaned


class UserRead(BaseModel):
    username: str
    role: str
    scopes: list[str]
