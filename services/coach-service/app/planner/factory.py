import logging
import os

from app.planner.base import Planner
from app.planner.fallback import FallbackPlanner
from app.planner.gemini import GeminiLLMClient
from app.planner.llm import AnthropicLLMClient, LLMPlanner

logger = logging.getLogger("trainflow.coach.factory")


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


def active_provider() -> str:
    """The provider that get_planner() would use right now: gemini | anthropic |
    fallback. Surfaced via /health so the UI can show the coach mode."""
    return _provider()


def get_planner() -> Planner:
    requested = os.getenv("COACH_PROVIDER", "auto").lower()
    provider = _provider()
    forced = requested in ("gemini", "anthropic", "fallback")
    how = "forced via COACH_PROVIDER" if forced else "auto-selected"

    if provider == "gemini":
        if not os.getenv("GEMINI_API_KEY"):
            logger.warning("Gemini provider selected but GEMINI_API_KEY is not set")
        logger.info("Coach using Gemini provider (%s)", how)
        return LLMPlanner(GeminiLLMClient())
    if provider == "anthropic":
        logger.info("Coach using Anthropic provider (%s)", how)
        return LLMPlanner(AnthropicLLMClient())

    logger.info("Coach using deterministic fallback planner (%s)", how)
    return FallbackPlanner()
