from app.planner.context import CoachContext
from app.planner.llm import LLMPlanner
from app.schemas import PlanRequest

EMPTY_CONTEXT = CoachContext()


def _request(**overrides) -> PlanRequest:
    payload = {
        "goal": "strength",
        "experience": "advanced",
        "days_per_week": 2,
        "session_minutes": 60,
    }
    payload.update(overrides)
    return PlanRequest(**payload)


class FakeLLM:
    """Returns a canned structured plan. Never touches the network."""

    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.calls = 0

    def generate_plan(self, system_prompt: str, user_prompt: str) -> dict:
        self.calls += 1
        return self.payload


def _all_item_ids(plan) -> list[int]:
    return [item.exercise_id for day in plan.days for item in day.items]


def test_llm_plan_is_parsed_and_returned(catalog):
    fake = FakeLLM(
        {
            "days": [
                {"focus": "Push", "items": [
                    {"exercise_id": 1, "sets": 5, "reps": "3-5", "rest_seconds": 180,
                     "rationale": "Main lift"},
                ]},
                {"focus": "Pull", "items": [
                    {"exercise_id": 3, "sets": 4, "reps": "6-8", "rest_seconds": 120},
                ]},
            ],
            "insights": ["LLM insight"],
            "notes": "from the model",
        }
    )
    plan = LLMPlanner(fake).generate(_request(), catalog, EMPTY_CONTEXT)

    assert fake.calls == 1
    assert plan.generated_by == "llm"
    assert plan.notes == "from the model"
    assert _all_item_ids(plan) == [1, 3]
    # Names are enriched from the catalog, not taken from the model.
    assert plan.days[0].items[0].exercise_name == "Barbell Bench Press"


def test_off_catalog_ids_are_dropped_and_day_topped_up(catalog):
    # Day 1 mixes a hallucinated id (999) with a valid one (1).
    # Day 2 is entirely hallucinated and must be topped up from fallback.
    fake = FakeLLM(
        {
            "days": [
                {"focus": "Push", "items": [
                    {"exercise_id": 999, "sets": 4, "reps": "8", "rest_seconds": 90},
                    {"exercise_id": 1, "sets": 4, "reps": "8", "rest_seconds": 90},
                ]},
                {"focus": "Ghost", "items": [
                    {"exercise_id": 12345, "sets": 4, "reps": "8", "rest_seconds": 90},
                ]},
            ],
            "insights": [],
        }
    )
    plan = LLMPlanner(fake).generate(_request(), catalog, EMPTY_CONTEXT)

    catalog_ids = {ex.id for ex in catalog}
    ids = _all_item_ids(plan)
    # No hallucinated id survives.
    assert set(ids).issubset(catalog_ids)
    assert 999 not in ids and 12345 not in ids
    # The valid pick stayed, and we still have a full 2-day plan.
    assert 1 in ids
    assert len(plan.days) == 2
    assert all(day.items for day in plan.days)


def test_avoid_and_equipment_enforced_on_llm_output(catalog):
    fake = FakeLLM(
        {
            "days": [
                {"focus": "Day", "items": [
                    {"exercise_id": 1, "sets": 4, "reps": "8", "rest_seconds": 90},
                    {"exercise_id": 3, "sets": 4, "reps": "8", "rest_seconds": 90},
                ]},
            ],
        }
    )
    # Avoid bench (1); only bodyweight allowed (pull up id 3 qualifies).
    plan = LLMPlanner(fake).generate(
        _request(days_per_week=1, avoid_exercise_ids=[1], available_equipment=["bodyweight"]),
        catalog,
        EMPTY_CONTEXT,
    )
    ids = _all_item_ids(plan)
    assert 1 not in ids
    by_id = {ex.id: ex for ex in catalog}
    assert all(by_id[i].equipment == "bodyweight" for i in ids)


def test_malformed_llm_output_degrades_to_fallback(catalog):
    fake = FakeLLM({"totally": "wrong shape"})
    plan = LLMPlanner(fake).generate(_request(), catalog, EMPTY_CONTEXT)

    assert plan.generated_by == "fallback"
    assert plan.days
