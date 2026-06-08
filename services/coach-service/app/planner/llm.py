"""LLM-backed planner. The LLM is central but bounded: it selects and orders
catalog exercises and explains its choices, but the catalog-only validation
layer reconciles every pick against the live catalog so it can never invent an
exercise. The LLM client is injected, so tests pass a fake and never hit the
network.
"""

import json
import logging
import os
import re
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

logger = logging.getLogger("trainflow.coach.planner")

# Redact any leaked secrets (e.g. ?key=... query params) before logging.
_SECRET_RE = re.compile(r"((?:key|api[_-]?key)=)[^&\s]+", re.IGNORECASE)


def _safe_error(exc: Exception) -> str:
    message = _SECRET_RE.sub(r"\1[REDACTED]", str(exc))
    return f"{type(exc).__name__}: {message}"


COACH_MODEL = os.getenv("COACH_MODEL", "claude-opus-4-8")

# A minimal example using the EXACT LLMPlanOutput schema, embedded in the prompt
# so the model emits the right field names.
_OUTPUT_EXAMPLE = {
    "days": [
        {
            "focus": "Upper body",
            "items": [
                {
                    "exercise_id": 1,
                    "sets": 4,
                    "reps": "8-12",
                    "rest_seconds": 90,
                    "rationale": "primary chest movement",
                }
            ],
        }
    ],
    "insights": ["short personalization note"],
    "notes": "optional overall note",
}

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
    "\nOUTPUT FORMAT (STRICT): Return a single JSON object with EXACTLY these "
    "top-level keys:\n"
    '  - "days" (REQUIRED): a JSON array of day objects.\n'
    '  - "insights": an array of short strings.\n'
    '  - "notes": a string or null.\n'
    'Do NOT use any other top-level key name (no "plan", "workout", "schedule", '
    '"week", etc.) — the array of days MUST be named "days".\n'
    'Each day object has "focus" (string) and "items" (array). Each item has '
    '"exercise_id" (integer from the catalog), "sets" (integer), "reps" '
    '(string, e.g. "8-12"), "rest_seconds" (integer), and optional "rationale" '
    "(string).\n"
    "Respond with ONLY the JSON object, matching this example exactly:\n"
    + json.dumps(_OUTPUT_EXAMPLE, indent=2)
)

# Safe aliases the model sometimes emits, mapped to the canonical schema keys.
# Normalization only fills a canonical key when it is missing — it never
# overwrites valid data, and strict Pydantic validation still runs afterwards.
_DAYS_ALIASES = ("plan", "workouts", "workout_days", "schedule", "week", "training_days")
_ITEMS_ALIASES = ("exercises", "movements", "workout", "sets_list")


def _normalize_output(raw: object) -> object:
    """Rename common top-level/day-level aliases to the canonical schema keys.
    Does not coerce types or invent values — anything still malformed is caught
    by Pydantic validation and falls back."""
    if not isinstance(raw, dict):
        return raw
    obj = dict(raw)

    if "days" not in obj:
        for alias in _DAYS_ALIASES:
            if isinstance(obj.get(alias), list):
                obj["days"] = obj.pop(alias)
                break

    days = obj.get("days")
    if isinstance(days, list):
        normalized_days = []
        for day in days:
            if isinstance(day, dict) and "items" not in day:
                day = dict(day)
                for alias in _ITEMS_ALIASES:
                    if isinstance(day.get(alias), list):
                        day["items"] = day.pop(alias)
                        break
            normalized_days.append(day)
        obj["days"] = normalized_days

    return obj


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

        client_name = self._client.__class__.__name__
        try:
            raw = self._client.generate_plan(
                _SYSTEM_PROMPT, _build_user_prompt(request, catalog, context)
            )
            output = LLMPlanOutput.model_validate(_normalize_output(raw))
        except Exception as exc:  # noqa: BLE001 - any LLM/parse failure degrades to fallback
            logger.warning(
                "LLM planner (%s) failed; falling back to deterministic planner. %s",
                client_name,
                _safe_error(exc),
            )
            return fallback_plan

        days = validate_llm_days(output.days, request, catalog, fallback_plan)
        logger.info("LLM planner (%s) produced a plan with %d day(s)", client_name, len(days))
        insights = context.insights or output.insights
        return WorkoutPlan(
            goal=request.goal,
            days_per_week=request.days_per_week,
            days=days,
            insights=insights,
            generated_by=self.name,
            notes=output.notes,
        )
