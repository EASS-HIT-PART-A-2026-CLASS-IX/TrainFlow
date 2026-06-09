def _register_login(client, username):
    client.post("/auth/register", json={"username": username, "password": "password123"})
    return client.post(
        "/auth/token", data={"username": username, "password": "password123"}
    ).json()["access_token"]


def _h(token):
    return {"Authorization": f"Bearer {token}"}


def _plan_body(focus="Push"):
    return {
        "goal": "hypertrophy",
        "generated_by": "gemini",
        "request": {"goal": "hypertrophy", "days_per_week": 3},
        "plan": {
            "goal": "hypertrophy",
            "days_per_week": 3,
            "generated_by": "gemini",
            "days": [{"focus": focus, "items": [
                {"exercise_id": 1, "exercise_name": "Bench", "sets": 4,
                 "reps": "8-12", "rest_seconds": 90}
            ]}],
            "insights": ["chest focus"],
        },
    }


def test_latest_is_404_when_none(client):
    token = _register_login(client, "amy")
    assert client.get("/plans/latest", headers=_h(token)).status_code == 404


def test_save_and_fetch_latest(client):
    token = _register_login(client, "amy")
    saved = client.post("/plans", json=_plan_body(), headers=_h(token))
    assert saved.status_code == 201
    body = saved.json()
    assert body["owner"] == "amy"
    assert body["generated_by"] == "gemini"
    assert body["plan"]["days"][0]["focus"] == "Push"

    latest = client.get("/plans/latest", headers=_h(token)).json()
    assert latest["id"] == body["id"]


def test_latest_returns_most_recent(client):
    token = _register_login(client, "amy")
    client.post("/plans", json=_plan_body(focus="Old"), headers=_h(token))
    client.post("/plans", json=_plan_body(focus="New"), headers=_h(token))
    latest = client.get("/plans/latest", headers=_h(token)).json()
    assert latest["plan"]["days"][0]["focus"] == "New"


def test_plans_are_owner_isolated(client):
    amy = _register_login(client, "amy")
    ben = _register_login(client, "ben")
    client.post("/plans", json=_plan_body(focus="Amy day"), headers=_h(amy))

    # Ben has no plan of his own.
    assert client.get("/plans/latest", headers=_h(ben)).status_code == 404
    assert client.get("/plans", headers=_h(ben)).json() == []
    # Amy sees only hers.
    amy_list = client.get("/plans", headers=_h(amy)).json()
    assert len(amy_list) == 1 and amy_list[0]["owner"] == "amy"


def test_save_requires_auth(client):
    assert client.post("/plans", json=_plan_body()).status_code == 401
