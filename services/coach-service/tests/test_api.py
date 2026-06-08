from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient

from app import auth
from app.main import app
from app.schemas import CatalogExercise

PLAN_BODY = {
    "goal": "hypertrophy",
    "experience": "intermediate",
    "days_per_week": 2,
    "session_minutes": 60,
}


def _token(scopes, expires_minutes=30):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "athlete",
        "scopes": scopes,
        "iat": now,
        "exp": now + timedelta(minutes=expires_minutes),
    }
    return jwt.encode(payload, auth.SECRET_KEY, algorithm=auth.ALGORITHM)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def patched_exercise_client(monkeypatch, catalog):
    class FakeClient:
        def __init__(self, token, base_url=None):
            pass

        def get_catalog(self):
            return catalog

        def get_history(self, limit):
            return []

    monkeypatch.setattr("app.routes.ExerciseClient", FakeClient)
    # Ensure deterministic fallback planner (no API key in test env).
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


def test_health_reports_provider(client, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("COACH_PROVIDER", raising=False)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "provider": "fallback"}


def test_plan_requires_auth(client):
    response = client.post("/plan", json=PLAN_BODY)
    assert response.status_code in (401, 403)


def test_plan_missing_scope_is_forbidden(client):
    token = _token(["history:read"])
    response = client.post("/plan", json=PLAN_BODY, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
    assert "coach:use" in response.json()["detail"]


def test_plan_expired_token_is_rejected(client):
    token = _token(["coach:use"], expires_minutes=-5)
    response = client.post("/plan", json=PLAN_BODY, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_plan_happy_path(client, patched_exercise_client):
    token = _token(["coach:use"])
    response = client.post("/plan", json=PLAN_BODY, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    body = response.json()
    assert body["generated_by"] == "fallback"
    assert len(body["days"]) == 2
    assert all(day["items"] for day in body["days"])


def test_plan_empty_catalog_is_422(client, monkeypatch):
    class EmptyClient:
        def __init__(self, token, base_url=None):
            pass

        def get_catalog(self):
            return []

        def get_history(self, limit):
            return []

    monkeypatch.setattr("app.routes.ExerciseClient", EmptyClient)
    token = _token(["coach:use"])
    response = client.post("/plan", json=PLAN_BODY, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 422
