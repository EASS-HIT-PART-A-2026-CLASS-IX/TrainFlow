import pytest

from app.planner.factory import get_planner
from app.planner.fallback import FallbackPlanner
from app.planner.llm import AnthropicLLMClient, LLMPlanner
from app.planner.ollama import OllamaLLMClient


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for var in ("COACH_PROVIDER", "COACH_USE_LLM", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(var, raising=False)


def test_auto_without_key_uses_fallback():
    assert isinstance(get_planner(), FallbackPlanner)


def test_auto_with_key_uses_anthropic(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    planner = get_planner()
    assert isinstance(planner, LLMPlanner)
    assert isinstance(planner._client, AnthropicLLMClient)


def test_explicit_ollama_provider(monkeypatch):
    monkeypatch.setenv("COACH_PROVIDER", "ollama")
    planner = get_planner()
    assert isinstance(planner, LLMPlanner)
    assert isinstance(planner._client, OllamaLLMClient)


def test_use_llm_false_forces_fallback(monkeypatch):
    monkeypatch.setenv("COACH_PROVIDER", "ollama")
    monkeypatch.setenv("COACH_USE_LLM", "false")
    assert isinstance(get_planner(), FallbackPlanner)
