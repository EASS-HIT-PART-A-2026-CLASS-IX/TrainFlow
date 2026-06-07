"""Catalog-only enforcement and repair. Regardless of what the LLM returns,
every item in the final plan must reference a real catalog exercise that
respects the request's equipment and avoid constraints. Days that end up empty
after filtering are topped up from the deterministic fallback plan so the
response is always complete and valid.
"""

from app.planner.base import equipment_allowed, scheme_for
from app.schemas import (
    CatalogExercise,
    LLMPlanDay,
    PlanItem,
    PlanRequest,
    WorkoutDay,
    WorkoutPlan,
)


def _item_is_valid(
    item_exercise_id: int,
    by_id: dict[int, CatalogExercise],
    available: list[str],
    avoid: set[int],
) -> bool:
    exercise = by_id.get(item_exercise_id)
    if exercise is None:
        return False
    if item_exercise_id in avoid:
        return False
    return equipment_allowed(exercise, available)


def validate_llm_days(
    llm_days: list[LLMPlanDay],
    request: PlanRequest,
    catalog: list[CatalogExercise],
    fallback_plan: WorkoutPlan,
) -> list[WorkoutDay]:
    by_id = {ex.id: ex for ex in catalog}
    available = [e.value for e in request.available_equipment]
    avoid = set(request.avoid_exercise_ids)
    default_sets, default_reps, default_rest = scheme_for(
        request.goal.value, request.experience.value
    )

    validated: list[WorkoutDay] = []
    for index in range(request.days_per_week):
        items: list[PlanItem] = []
        if index < len(llm_days):
            for raw in llm_days[index].items:
                if not _item_is_valid(raw.exercise_id, by_id, available, avoid):
                    continue
                exercise = by_id[raw.exercise_id]
                items.append(
                    PlanItem(
                        exercise_id=exercise.id,
                        exercise_name=exercise.name,
                        sets=_clamp(raw.sets, 1, 10, default_sets),
                        reps=raw.reps or default_reps,
                        rest_seconds=_clamp(raw.rest_seconds, 10, 600, default_rest),
                        rationale=raw.rationale,
                    )
                )

        if items:
            focus = llm_days[index].focus if index < len(llm_days) else "Workout"
            validated.append(WorkoutDay(focus=focus or "Workout", items=items))
        elif index < len(fallback_plan.days):
            # Top up an empty/invalid day from the deterministic fallback.
            validated.append(fallback_plan.days[index])

    # Never return an empty plan.
    return validated or fallback_plan.days


def _clamp(value: int, low: int, high: int, default: int) -> int:
    if value is None:
        return default
    return max(low, min(high, value))
