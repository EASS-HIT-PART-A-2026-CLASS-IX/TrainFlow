import json

import pytest

from app.planner.gemini import GeminiLLMClient


class FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _gemini_envelope(text: str) -> dict:
    return {"candidates": [{"content": {"parts": [{"text": text}]}}]}


def test_generate_plan_parses_gemini_response(monkeypatch):
    plan_json = {
        "days": [{"focus": "Push", "items": [
            {"exercise_id": 1, "sets": 4, "reps": "8-12", "rest_seconds": 90},
        ]}],
        "insights": [],
        "notes": "from gemini",
    }
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["body"] = json
        return FakeResponse(_gemini_envelope(__import__("json").dumps(plan_json)))

    monkeypatch.setattr("app.planner.gemini.httpx.post", fake_post)

    result = GeminiLLMClient(api_key="test-key", model="gemini-2.0-flash").generate_plan(
        "system", "user"
    )

    assert result == plan_json
    assert captured["url"].endswith("/models/gemini-2.0-flash:generateContent")
    # The key travels in a header, never in the URL/query string.
    assert captured["headers"]["x-goog-api-key"] == "test-key"
    assert "key=" not in captured["url"]
    # JSON mode is requested so the model returns a single JSON document.
    assert captured["body"]["generationConfig"]["responseMimeType"] == "application/json"
    assert captured["body"]["systemInstruction"]["parts"][0]["text"] == "system"


def test_generate_plan_raises_on_invalid_json(monkeypatch):
    def fake_post(url, headers=None, json=None, timeout=None):
        return FakeResponse(_gemini_envelope("not json"))

    monkeypatch.setattr("app.planner.gemini.httpx.post", fake_post)

    with pytest.raises(json.JSONDecodeError):
        GeminiLLMClient(api_key="k").generate_plan("s", "u")


def test_generate_plan_raises_on_no_candidates(monkeypatch):
    def fake_post(url, headers=None, json=None, timeout=None):
        return FakeResponse({"promptFeedback": {"blockReason": "SAFETY"}})

    monkeypatch.setattr("app.planner.gemini.httpx.post", fake_post)

    with pytest.raises(ValueError, match="no candidates"):
        GeminiLLMClient(api_key="k").generate_plan("s", "u")


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        GeminiLLMClient(api_key="").generate_plan("s", "u")
