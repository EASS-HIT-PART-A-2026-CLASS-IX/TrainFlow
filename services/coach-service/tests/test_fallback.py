from app.planner.context import CoachContext, build_context
from app.planner.fallback import FallbackPlanner
from app.schemas import PlanRequest

EMPTY_CONTEXT = CoachContext()


def _request(**overrides) -> PlanRequest:
    payload = {
        "goal": "hypertrophy",
        "experience": "intermediate",
        "days_per_week": 3,
        "session_minutes": 60,
    }
    payload.update(overrides)
    return PlanRequest(**payload)


def _all_item_ids(plan) -> list[int]:
    return [item.exercise_id for day in plan.days for item in day.items]


def test_plan_has_requested_days_and_only_catalog_ids(catalog):
    plan = FallbackPlanner().generate(_request(days_per_week=3), catalog, EMPTY_CONTEXT)

    assert plan.generated_by == "fallback"
    assert len(plan.days) == 3
    assert all(day.items for day in plan.days)
    catalog_ids = {ex.id for ex in catalog}
    assert set(_all_item_ids(plan)).issubset(catalog_ids)


def test_respects_equipment_filter(catalog):
    plan = FallbackPlanner().generate(
        _request(available_equipment=["bodyweight"]), catalog, EMPTY_CONTEXT
    )
    by_id = {ex.id: ex for ex in catalog}
    assert all(by_id[eid].equipment == "bodyweight" for eid in _all_item_ids(plan))


def test_respects_avoid_list(catalog):
    plan = FallbackPlanner().generate(
        _request(avoid_exercise_ids=[1, 2]), catalog, EMPTY_CONTEXT
    )
    assert 1 not in _all_item_ids(plan)
    assert 2 not in _all_item_ids(plan)


def test_history_rebalances_toward_undertrained(catalog, chest_heavy_history):
    context = build_context(chest_heavy_history, catalog)
    plan = FallbackPlanner().generate(_request(), catalog, context)
    by_id = {ex.id: ex for ex in catalog}

    trained_muscles = {
        m for eid in _all_item_ids(plan) for m in by_id[eid].primary_muscles
    }
    # Recent sessions were all chest; the plan should add under-trained work
    # such as back/legs rather than piling on more chest.
    assert {"back", "quadriceps", "shoulders"} & trained_muscles


def test_recently_used_is_deprioritized(catalog, chest_heavy_history):
    context = build_context(chest_heavy_history, catalog)
    # Small pool/short session so only the top picks are taken.
    plan = FallbackPlanner().generate(
        _request(days_per_week=1, session_minutes=24), catalog, context
    )
    # Bench press (id 1) was used most recently and should not be a top pick
    # when fresher, under-trained options exist.
    assert 1 not in _all_item_ids(plan)
