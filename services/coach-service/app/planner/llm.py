"""LLM-backed planner. The LLM is central but bounded: it selects and orders
catalog exercises and explains its choices, but the catalog-only validation
layer reconciles every pick against the live catalog so it can never invent an
exercise. The LLM client is injected, so tests pass a fake and never hit the
network.
"""

import json
import os
from typing import Protocol

from app.planner.context import CoachContext
from app.planner.fallback import FallbackPlanner
from app.planner.validation import validate_llm_days
from app.schemas import (
    CatalogExercise,
    LLMPlanOutput,
    PlanRequest,
    WorkoutPlan,
)

COACH_MODEL = os.getenv("COACH_MODEL", "claude-opus-4-8")

_SYSTEM_PROMPT = (
    "You are TrainFlow Coach, an expert strength & conditioning planner. "
    "You design structured workout plans. Hard rules:\n"
    "- You may ONLY select exercises from the provided catalog, referenced by "
    "their integer exercise_id.\n"
    "- Never invent exercises or ids.\n"
    "- Respect the athlete's available equipment, target muscles, and the "
    "exercises they want to avoid.\n"
    "- Use the recent-history signals to personalize: avoid recently overused "
    "exercises and rebalance toward under-trained muscle groups.\n"
    "- Distribute work across the requested number of training days.\n"
    "Return one plan that matches the requested goal and schedule."
)


class LLMClient(Protocol):
    def generate_plan(self, system_prompt: str, user_prompt: str) -> dict: ...


class AnthropicLLMClient:
    """Real client. Constructed lazily so importing this module never requires
    an API key."""

    def __init__(self, model: str = COACH_MODEL) -> None:
        self._model = model

    def generate_plan(self, system_prompt: str, user_prompt: str) -> dict:
        import anthropic

        client = anthropic.Anthropic()
        response = client.messages.parse(
            model=self._model,
            max_tokens=4000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            output_format=LLMPlanOutput,
        )
        if response.parsed_output is None:
            raise ValueError("LLM did not return a parseable plan")
        return response.parsed_output.model_dump()


def _build_user_prompt(
    request: PlanRequest,
    catalog: list[CatalogExercise],
    context: CoachContext,
) -> str:
    catalog_lines = [
        {
            "id": ex.id,
            "name": ex.name,
            "primary_muscles": ex.primary_muscles,
            "equipment": ex.equipment,
            "difficulty": ex.difficulty,
        }
        for ex in catalog
    ]
    payload = {
        "request": request.model_dump(mode="json"),
        "catalog": catalog_lines,
        "recent_signals": {
            "recently_used_exercise_ids": context.recently_used_exercise_ids,
            "recently_trained_muscles": context.recently_trained_muscles,
            "volume_by_muscle": context.volume_by_muscle,
        },
    }
    return (
        "Design a workout plan from this catalog and athlete context. "
        "Use only exercise_ids present in the catalog.\n\n"
        + json.dumps(payload, indent=2)
    )


class LLMPlanner:
    name = "llm"

    def __init__(self, client: LLMClient) -> None:
        self._client = client
        self._fallback = FallbackPlanner()

    def generate(
        self,
        request: PlanRequest,
        catalog: list[CatalogExercise],
        context: CoachContext,
    ) -> WorkoutPlan:
        fallback_plan = self._fallback.generate(request, catalog, context)

        try:
            raw = self._client.generate_plan(
                _SYSTEM_PROMPT, _build_user_prompt(request, catalog, context)
            )
            output = LLMPlanOutput.model_validate(raw)
        except Exception:  # noqa: BLE001 - any LLM/parse failure degrades to fallback
            return fallback_plan

        days = validate_llm_days(output.days, request, catalog, fallback_plan)
        insights = context.insights or output.insights
        return WorkoutPlan(
            goal=request.goal,
            days_per_week=request.days_per_week,
            days=days,
            insights=insights,
            generated_by=self.name,
            notes=output.notes,
        )
