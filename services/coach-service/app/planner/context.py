"""Derive lightweight, deterministic personalization signals from recent
workout history. This is the "feels intelligent" layer — pure Python, no LLM,
fully testable. The same signals feed both the LLM prompt and the fallback
planner so personalization works in either mode.
"""

from dataclasses import dataclass, field

from app.schemas import CatalogExercise

# Secondary muscles count for less recovery cost than primary movers.
_SECONDARY_WEIGHT = 0.5


@dataclass
class CoachContext:
    recently_used_exercise_ids: list[int] = field(default_factory=list)
    recently_trained_muscles: list[str] = field(default_factory=list)
    volume_by_muscle: dict[str, float] = field(default_factory=dict)
    insights: list[str] = field(default_factory=list)


def build_context(
    history: list[dict],
    catalog: list[CatalogExercise],
) -> CoachContext:
    """history is newest-first, as returned by exercise-service GET /sessions."""
    by_id = {ex.id: ex for ex in catalog}
    volume_by_muscle: dict[str, float] = {}
    recently_used: list[int] = []

    # Weight more recent sessions higher (recency decay).
    for position, session in enumerate(history):
        recency_weight = 1.0 / (1 + position)
        for item in session.get("exercises", []):
            exercise_id = item.get("exercise_id")
            if exercise_id not in by_id:
                continue
            if exercise_id not in recently_used:
                recently_used.append(exercise_id)
            sets = item.get("sets", 0) or 0
            exercise = by_id[exercise_id]
            for muscle in exercise.primary_muscles:
                volume_by_muscle[muscle] = (
                    volume_by_muscle.get(muscle, 0.0) + sets * recency_weight
                )
            for muscle in exercise.secondary_muscles:
                volume_by_muscle[muscle] = (
                    volume_by_muscle.get(muscle, 0.0)
                    + sets * recency_weight * _SECONDARY_WEIGHT
                )

    recently_trained_muscles = sorted(
        volume_by_muscle,
        key=lambda muscle: (-volume_by_muscle[muscle], muscle),
    )

    insights = _build_insights(recently_trained_muscles, volume_by_muscle, recently_used, by_id)

    return CoachContext(
        recently_used_exercise_ids=recently_used,
        recently_trained_muscles=recently_trained_muscles,
        volume_by_muscle=volume_by_muscle,
        insights=insights,
    )


def _build_insights(
    recently_trained_muscles: list[str],
    volume_by_muscle: dict[str, float],
    recently_used: list[int],
    by_id: dict[int, CatalogExercise],
) -> list[str]:
    if not recently_trained_muscles:
        return ["No recent workout history — building a balanced plan from your preferences."]

    insights: list[str] = []
    top = recently_trained_muscles[0]
    insights.append(f"You trained {top} heavily in recent sessions.")

    # An under-trained muscle is one with little or no recent volume.
    trained = set(volume_by_muscle)
    if len(recently_trained_muscles) >= 2:
        bottom = recently_trained_muscles[-1]
        if volume_by_muscle[bottom] < volume_by_muscle[top]:
            insights.append(f"Adding more {bottom} volume to balance recent training.")

    if recently_used:
        names = [by_id[eid].name for eid in recently_used[:3] if eid in by_id]
        if names:
            insights.append("Recently used: " + ", ".join(names) + ".")
    return insights
