import json

from app.planner.ollama import OllamaLLMClient


class FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_generate_plan_parses_ollama_chat_response(monkeypatch):
    plan_json = {
        "days": [{"focus": "Push", "items": [
            {"exercise_id": 1, "sets": 4, "reps": "8-12", "rest_seconds": 90},
        ]}],
        "insights": [],
        "notes": "local model",
    }
    captured = {}

    def fake_post(url, json=None, timeout=None):
        captured["url"] = url
        captured["body"] = json
        # Ollama returns the structured content as a JSON string in message.content.
        return FakeResponse({"message": {"content": __import__("json").dumps(plan_json)}})

    monkeypatch.setattr("app.planner.ollama.httpx.post", fake_post)

    result = OllamaLLMClient(model="llama3.1", base_url="http://ollama:11434").generate_plan(
        "system", "user"
    )

    assert result == plan_json
    assert captured["url"] == "http://ollama:11434/api/chat"
    # The request constrains output to the plan schema and disables streaming.
    assert captured["body"]["model"] == "llama3.1"
    assert captured["body"]["stream"] is False
    assert captured["body"]["format"]["type"] == "object"


def test_generate_plan_raises_on_invalid_json(monkeypatch):
    def fake_post(url, json=None, timeout=None):
        return FakeResponse({"message": {"content": "not json"}})

    monkeypatch.setattr("app.planner.ollama.httpx.post", fake_post)

    try:
        OllamaLLMClient().generate_plan("s", "u")
        raised = False
    except json.JSONDecodeError:
        raised = True
    assert raised
