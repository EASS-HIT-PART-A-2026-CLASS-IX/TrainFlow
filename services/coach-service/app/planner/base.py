from typing import Protocol

from app.planner.context import CoachContext
from app.schemas import CatalogExercise, PlanRequest, WorkoutPlan


class Planner(Protocol):
    name: str

    def generate(
        self,
        request: PlanRequest,
        catalog: list[CatalogExercise],
        context: CoachContext,
    ) -> WorkoutPlan: ...


# Sets / reps / rest defaults by training goal.
GOAL_SCHEME: dict[str, tuple[int, str, int]] = {
    "strength": (5, "3-5", 180),
    "hypertrophy": (4, "8-12", 75),
    "endurance": (3, "15-20", 45),
    "general": (3, "10-12", 60),
}


def scheme_for(goal: str, experience: str) -> tuple[int, str, int]:
    sets, reps, rest = GOAL_SCHEME.get(goal, GOAL_SCHEME["general"])
    if experience == "beginner":
        sets = max(2, sets - 1)
    return sets, reps, rest


def equipment_allowed(exercise: CatalogExercise, available: list[str]) -> bool:
    # Empty available list means "no equipment constraint".
    return not available or exercise.equipment in available
