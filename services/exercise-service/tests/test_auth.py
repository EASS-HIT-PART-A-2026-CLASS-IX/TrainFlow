from datetime import timedelta

from app.auth import create_access_token, hash_password, verify_password
from app.seed import ATHLETE_SCOPES


def _exercise_payload():
    return {
        "name": "Push Up",
        "primary_muscles": ["chest"],
        "secondary_muscles": ["triceps"],
        "equipment": "bodyweight",
        "difficulty": "beginner",
    }


def test_password_is_hashed_not_plaintext():
    hashed = hash_password("secret")
    assert hashed != "secret"
    assert verify_password("secret", hashed)
    assert not verify_password("wrong", hashed)


def test_login_returns_token(client, admin_token):
    response = client.post(
        "/auth/token",
        data={"username": "admin", "password": "secret"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert "exercises:write" in body["scopes"]


def test_login_with_wrong_password_is_rejected(client, admin_token):
    response = client.post(
        "/auth/token",
        data={"username": "admin", "password": "nope"},
    )

    assert response.status_code == 401


def test_write_without_token_is_unauthorized(client):
    response = client.post("/exercises", json=_exercise_payload())

    assert response.status_code == 401


def test_expired_token_is_rejected(client, admin_token):
    expired = create_access_token(
        "admin",
        ["exercises:write"],
        expires_delta=timedelta(minutes=-5),
    )
    response = client.post(
        "/exercises",
        json=_exercise_payload(),
        headers={"Authorization": f"Bearer {expired}"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Token has expired"


def test_missing_scope_is_forbidden(client, athlete_token):
    # The athlete token carries history/coach scopes but not exercises:write.
    assert "exercises:write" not in ATHLETE_SCOPES
    response = client.post(
        "/exercises",
        json=_exercise_payload(),
        headers={"Authorization": f"Bearer {athlete_token}"},
    )

    assert response.status_code == 403
    assert "Missing scope: exercises:write" in response.json()["detail"]


def test_writer_token_can_create(auth_client):
    response = auth_client.post("/exercises", json=_exercise_payload())

    assert response.status_code == 201
