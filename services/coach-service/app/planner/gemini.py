"""Free-tier-friendly cloud LLM client backed by Google Gemini.

Implements the same LLMClient protocol as AnthropicLLMClient, so the planner,
catalog-only validation, and fallback logic are all unchanged. Calls the Gemini
REST API (JSON mode) with httpx — no extra SDK dependency. The validation/repair
layer still guarantees catalog-only results regardless of the model's output.

The API key is sent in the ``x-goog-api-key`` header (not a URL query param) so
it never appears in request URLs, error messages, or logs.
"""

import json
import os

import httpx

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
GEMINI_API_URL = os.getenv(
    "GEMINI_API_URL", "https://generativelanguage.googleapis.com/v1beta"
)


class GeminiLLMClient:
    def __init__(
        self,
        api_key: str | None = None,
        model: str = GEMINI_MODEL,
        base_url: str = GEMINI_API_URL,
    ) -> None:
        self._api_key = api_key or os.getenv("GEMINI_API_KEY")
        self._model = model
        self._base_url = base_url.rstrip("/")

    def generate_plan(self, system_prompt: str, user_prompt: str) -> dict:
        if not self._api_key:
            raise ValueError("GEMINI_API_KEY is not set")

        response = httpx.post(
            f"{self._base_url}/models/{self._model}:generateContent",
            headers={"x-goog-api-key": self._api_key},
            json={
                "systemInstruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                # JSON mode: the model must return a single JSON document.
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "temperature": 0.4,
                },
            },
            timeout=120.0,
        )
        response.raise_for_status()
        data = response.json()

        candidates = data.get("candidates")
        if not candidates:
            # No candidates usually means the prompt/response was blocked.
            raise ValueError(
                f"Gemini returned no candidates (prompt_feedback={data.get('promptFeedback')})"
            )
        text = candidates[0]["content"]["parts"][0]["text"]
        return json.loads(text)
