from enum import Enum

from pydantic import BaseModel, Field


class Goal(str, Enum):
    strength = "strength"
    hypertrophy = "hypertrophy"
    endurance = "endurance"
    general = "general"


class Difficulty(str, Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class Equipment(str, Enum):
    bodyweight = "bodyweight"
    dumbbell = "dumbbell"
    barbell = "barbell"
    machine = "machine"
    cable = "cable"
    smith = "smith"


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


# ---------------------------------------------------------------------------
# Catalog & history (as fetched from exercise-service over HTTP).
# ---------------------------------------------------------------------------
class CatalogExercise(BaseModel):
    id: int
    name: str
    primary_muscles: list[str] = Field(default_factory=list)
    secondary_muscles: list[str] = Field(default_factory=list)
    equipment: str
    difficulty: str


# ---------------------------------------------------------------------------
# Plan request / response (public coach API).
# ---------------------------------------------------------------------------
class PlanRequest(BaseModel):
    goal: Goal
    experience: Difficulty
    days_per_week: int = Field(ge=1, le=7)
    session_minutes: int = Field(ge=15, le=120)
    available_equipment: list[Equipment] = Field(default_factory=list)
    target_muscles: list[MuscleGroup] = Field(default_factory=list)
    avoid_exercise_ids: list[int] = Field(default_factory=list)
    history_limit: int = Field(default=5, ge=0, le=20)


class PlanItem(BaseModel):
    exercise_id: int
    exercise_name: str
    sets: int = Field(ge=1, le=10)
    reps: str
    rest_seconds: int = Field(ge=10, le=600)
    rationale: str | None = None


class WorkoutDay(BaseModel):
    focus: str
    items: list[PlanItem]


class WorkoutPlan(BaseModel):
    goal: Goal
    days_per_week: int
    days: list[WorkoutDay]
    insights: list[str] = Field(default_factory=list)
    generated_by: str  # "llm" | "fallback"
    notes: str | None = None


# ---------------------------------------------------------------------------
# Constrained schema the LLM fills in. Kept minimal so structured-output
# validation is reliable; exercise names/validation are added afterwards.
# ---------------------------------------------------------------------------
class LLMPlanItem(BaseModel):
    exercise_id: int
    sets: int
    reps: str
    rest_seconds: int
    rationale: str | None = None


class LLMPlanDay(BaseModel):
    focus: str
    items: list[LLMPlanItem]


class LLMPlanOutput(BaseModel):
    days: list[LLMPlanDay]
    insights: list[str] = Field(default_factory=list)
    notes: str | None = None
