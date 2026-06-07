import pytest

from app.planner.factory import get_planner
from app.planner.fallback import FallbackPlanner
from app.planner.gemini import GeminiLLMClient
from app.planner.llm import AnthropicLLMClient, LLMPlanner


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for var in ("COACH_PROVIDER", "COACH_USE_LLM", "GEMINI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(var, raising=False)


def test_auto_without_keys_uses_fallback():
    assert isinstance(get_planner(), FallbackPlanner)


def test_auto_prefers_gemini_when_key_present(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "g-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "a-key")
    planner = get_planner()
    assert isinstance(planner, LLMPlanner)
    assert isinstance(planner._client, GeminiLLMClient)


def test_auto_falls_back_to_anthropic_when_only_anthropic_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "a-key")
    planner = get_planner()
    assert isinstance(planner, LLMPlanner)
    assert isinstance(planner._client, AnthropicLLMClient)


def test_explicit_gemini_provider(monkeypatch):
    monkeypatch.setenv("COACH_PROVIDER", "gemini")
    planner = get_planner()
    assert isinstance(planner, LLMPlanner)
    assert isinstance(planner._client, GeminiLLMClient)


def test_explicit_anthropic_provider(monkeypatch):
    monkeypatch.setenv("COACH_PROVIDER", "anthropic")
    planner = get_planner()
    assert isinstance(planner._client, AnthropicLLMClient)


def test_use_llm_false_forces_fallback(monkeypatch):
    monkeypatch.setenv("COACH_PROVIDER", "gemini")
    monkeypatch.setenv("COACH_USE_LLM", "false")
    assert isinstance(get_planner(), FallbackPlanner)


def test_forced_gemini_generates_llm_plan(monkeypatch, catalog):
    """End-to-end: COACH_PROVIDER=gemini with a mocked successful Gemini
    response yields an LLM plan (not a fallback)."""
    monkeypatch.setenv("COACH_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "g-key")

    plan_json = {
        "days": [{"focus": "Push", "items": [
            {"exercise_id": 1, "sets": 4, "reps": "8-12", "rest_seconds": 90},
        ]}],
        "insights": [],
        "notes": "ok",
    }

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"candidates": [{"content": {"parts": [
                {"text": __import__("json").dumps(plan_json)}
            ]}}]}

    monkeypatch.setattr("app.planner.gemini.httpx.post", lambda *a, **k: FakeResponse())

    from app.planner.context import CoachContext
    from app.schemas import PlanRequest

    planner = get_planner()
    assert isinstance(planner, LLMPlanner)
    assert isinstance(planner._client, GeminiLLMClient)

    plan = planner.generate(
        PlanRequest(goal="hypertrophy", experience="intermediate",
                    days_per_week=1, session_minutes=60),
        catalog,
        CoachContext(),
    )
    assert plan.generated_by == "llm"
    assert plan.days and plan.days[0].items
    assert plan.days[0].items[0].exercise_id == 1
