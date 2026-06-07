import os

from app.planner.base import Planner
from app.planner.fallback import FallbackPlanner
from app.planner.llm import AnthropicLLMClient, LLMPlanner


def get_planner() -> Planner:
    """Use the LLM planner when an API key is configured and not explicitly
    disabled; otherwise fall back to the deterministic planner."""
    use_llm = os.getenv("COACH_USE_LLM", "true").lower() != "false"
    if use_llm and os.getenv("ANTHROPIC_API_KEY"):
        return LLMPlanner(AnthropicLLMClient())
    return FallbackPlanner()
