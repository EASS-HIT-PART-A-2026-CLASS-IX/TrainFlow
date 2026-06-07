import os

from app.planner.base import Planner
from app.planner.fallback import FallbackPlanner
from app.planner.gemini import GeminiLLMClient
from app.planner.llm import AnthropicLLMClient, LLMPlanner


def _provider() -> str:
    """Resolve the active provider.

    COACH_PROVIDER (auto | gemini | anthropic | fallback) takes precedence.
    "auto" (the default) prefers Gemini (free cloud tier) when GEMINI_API_KEY is
    set, then Anthropic when ANTHROPIC_API_KEY is set, otherwise the
    deterministic fallback.
    """
    if os.getenv("COACH_USE_LLM", "true").lower() == "false":
        return "fallback"

    provider = os.getenv("COACH_PROVIDER", "auto").lower()
    if provider in ("gemini", "anthropic", "fallback"):
        return provider
    # auto
    if os.getenv("GEMINI_API_KEY"):
        return "gemini"
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    return "fallback"


def get_planner() -> Planner:
    provider = _provider()
    if provider == "gemini":
        return LLMPlanner(GeminiLLMClient())
    if provider == "anthropic":
        return LLMPlanner(AnthropicLLMClient())
    return FallbackPlanner()
