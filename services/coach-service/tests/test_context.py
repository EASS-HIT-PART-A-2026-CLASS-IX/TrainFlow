from app.planner.context import build_context


def test_chest_heavy_history_signals(catalog, chest_heavy_history):
    context = build_context(chest_heavy_history, catalog)

    # Chest was trained the most, so it leads recently-trained muscles.
    assert context.recently_trained_muscles[0] == "chest"
    # Both bench and incline press were used.
    assert 1 in context.recently_used_exercise_ids
    assert 2 in context.recently_used_exercise_ids
    # Chest carries more volume than any leg/back muscle (which is zero).
    assert context.volume_by_muscle["chest"] > context.volume_by_muscle.get("back", 0.0)


def test_chest_heavy_insights(catalog, chest_heavy_history):
    context = build_context(chest_heavy_history, catalog)
    joined = " ".join(context.insights).lower()

    assert "chest" in joined
    # Names of recently used exercises surface in the insights.
    assert "bench press" in joined.lower()


def test_empty_history_is_safe(catalog):
    context = build_context([], catalog)

    assert context.recently_used_exercise_ids == []
    assert context.recently_trained_muscles == []
    assert context.volume_by_muscle == {}
    assert context.insights  # a helpful default message is present


def test_unknown_exercise_ids_ignored(catalog):
    history = [{"id": 9, "date": "2026-06-06", "goal": "general",
                "exercises": [{"exercise_id": 999, "sets": 5, "reps": 5}]}]
    context = build_context(history, catalog)

    assert context.recently_used_exercise_ids == []
    assert context.volume_by_muscle == {}
