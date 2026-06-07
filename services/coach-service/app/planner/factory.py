import os

from app.planner.base import Planner
from app.planner.fallback import FallbackPlanner
from app.planner.llm import AnthropicLLMClient, LLMPlanner
from app.planner.ollama import OllamaLLMClient


def _provider() -> str:
    """Resolve the active provider.

    COACH_PROVIDER (anthropic | ollama | fallback | auto) takes precedence.
    "auto" (the default) uses Anthropic when a key is present, else the
    deterministic fallback. Set COACH_PROVIDER=ollama to use a free local model.
    """
    if os.getenv("COACH_USE_LLM", "true").lower() == "false":
        return "fallback"

    provider = os.getenv("COACH_PROVIDER", "auto").lower()
    if provider in ("anthropic", "ollama", "fallback"):
        return provider
    # auto
    return "anthropic" if os.getenv("ANTHROPIC_API_KEY") else "fallback"


def get_planner() -> Planner:
    provider = _provider()
    if provider == "ollama":
        return LLMPlanner(OllamaLLMClient())
    if provider == "anthropic":
        return LLMPlanner(AnthropicLLMClient())
    return FallbackPlanner()
