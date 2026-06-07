from app.auth import create_access_token

EX_PAYLOAD = {
    "name": "Barbell Bench Press",
    "primary_muscles": ["chest"],
    "secondary_muscles": ["triceps"],
    "equipment": "barbell",
    "difficulty": "intermediate",
}


def _create_exercise(auth_client, **overrides) -> int:
    payload = {**EX_PAYLOAD, **overrides}
    response = auth_client.post("/exercises", json=payload)
    assert response.status_code == 201
    return response.json()["id"]


def _session_payload(exercise_id: int, **overrides) -> dict:
    payload = {
        "date": "2026-06-05",
        "goal": "hypertrophy",
        "notes": "Chest day",
        "exercises": [{"exercise_id": exercise_id, "sets": 4, "reps": 8, "weight": 60.0}],
    }
    payload.update(overrides)
    return payload


def test_create_session_with_nested_exercises(auth_client):
    exercise_id = _create_exercise(auth_client)
    response = auth_client.post("/sessions", json=_session_payload(exercise_id))

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == 1
    assert data["goal"] == "hypertrophy"
    assert len(data["exercises"]) == 1
    item = data["exercises"][0]
    assert item["exercise_id"] == exercise_id
    assert item["exercise_name"] == "Barbell Bench Press"
    assert item["sets"] == 4


def test_reject_unknown_exercise_id(auth_client):
    response = auth_client.post("/sessions", json=_session_payload(9999))

    assert response.status_code == 422
    assert "9999" in response.json()["detail"]


def test_reject_out_of_range_sets(auth_client):
    exercise_id = _create_exercise(auth_client)
    payload = _session_payload(exercise_id)
    payload["exercises"][0]["sets"] = 99
    response = auth_client.post("/sessions", json=payload)

    assert response.status_code == 422


def test_list_sessions_newest_first_and_limit(auth_client):
    exercise_id = _create_exercise(auth_client)
    auth_client.post("/sessions", json=_session_payload(exercise_id, date="2026-06-01"))
    auth_client.post("/sessions", json=_session_payload(exercise_id, date="2026-06-05"))
    auth_client.post("/sessions", json=_session_payload(exercise_id, date="2026-06-03"))

    response = auth_client.get("/sessions", params={"limit": 2})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["date"] == "2026-06-05"
    assert data[1]["date"] == "2026-06-03"


def test_get_session_by_id(auth_client):
    exercise_id = _create_exercise(auth_client)
    created = auth_client.post("/sessions", json=_session_payload(exercise_id)).json()
    response = auth_client.get(f"/sessions/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_missing_session_returns_404(auth_client):
    response = auth_client.get("/sessions/404")

    assert response.status_code == 404


def test_delete_session_cascades(auth_client):
    exercise_id = _create_exercise(auth_client)
    created = auth_client.post("/sessions", json=_session_payload(exercise_id)).json()
    delete = auth_client.delete(f"/sessions/{created['id']}")
    get = auth_client.get(f"/sessions/{created['id']}")

    assert delete.status_code == 204
    assert get.status_code == 404


def test_history_requires_auth(client):
    response = client.get("/sessions")

    assert response.status_code == 401


def test_history_requires_read_scope(client, admin_token):
    # admin user exists in the DB, but mint a token with no scopes.
    token = create_access_token("admin", [])
    response = client.get("/sessions", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403
    assert "history:read" in response.json()["detail"]
