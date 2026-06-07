import json

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

    def fake_post(url, params=None, json=None, timeout=None):
        captured["url"] = url
        captured["params"] = params
        captured["body"] = json
        return FakeResponse(_gemini_envelope(__import__("json").dumps(plan_json)))

    monkeypatch.setattr("app.planner.gemini.httpx.post", fake_post)

    result = GeminiLLMClient(api_key="test-key", model="gemini-2.0-flash").generate_plan(
        "system", "user"
    )

    assert result == plan_json
    assert captured["url"].endswith("/models/gemini-2.0-flash:generateContent")
    assert captured["params"] == {"key": "test-key"}
    # JSON mode is requested so the model returns a single JSON document.
    assert captured["body"]["generationConfig"]["response_mime_type"] == "application/json"
    assert captured["body"]["system_instruction"]["parts"][0]["text"] == "system"


def test_generate_plan_raises_on_invalid_json(monkeypatch):
    def fake_post(url, params=None, json=None, timeout=None):
        return FakeResponse(_gemini_envelope("not json"))

    monkeypatch.setattr("app.planner.gemini.httpx.post", fake_post)

    try:
        GeminiLLMClient(api_key="k").generate_plan("s", "u")
        raised = False
    except json.JSONDecodeError:
        raised = True
    assert raised
