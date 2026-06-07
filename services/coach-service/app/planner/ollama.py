"""Free, fully-local LLM client backed by Ollama (https://ollama.com).

No API key, no billing, no data leaving the machine. Implements the same
LLMClient protocol as AnthropicLLMClient, so the planner, catalog-only
validation, and fallback logic are all unchanged. Uses Ollama's structured-
output `format` parameter (a JSON schema) so the model returns parseable JSON;
the validation/repair layer still guarantees catalog-only results regardless.
"""

import json
import os

import httpx

from app.schemas import LLMPlanOutput

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")


class OllamaLLMClient:
    def __init__(self, model: str = OLLAMA_MODEL, base_url: str = OLLAMA_URL) -> None:
        self._model = model
        self._base_url = base_url.rstrip("/")

    def generate_plan(self, system_prompt: str, user_prompt: str) -> dict:
        response = httpx.post(
            f"{self._base_url}/api/chat",
            json={
                "model": self._model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                # Constrain output to the plan schema (Ollama >= 0.5).
                "format": LLMPlanOutput.model_json_schema(),
                "stream": False,
                "options": {"temperature": 0.4},
            },
            timeout=120.0,
        )
        response.raise_for_status()
        content = response.json()["message"]["content"]
        return json.loads(content)
