NOT_FOUND_DETAIL = "Exercise not found"


def exercise_payload(**overrides):
    payload = {
        "name": "Push Up",
        "primary_muscles": ["chest"],
        "secondary_muscles": ["triceps", "shoulders"],
        "equipment": "bodyweight",
        "difficulty": "beginner",
        "instructions": "Keep your body in a straight line.",
        "media_url": "https://example.com/push-up",
    }
    payload.update(overrides)
    return payload


def test_create_valid_exercise_successfully(auth_client):
    response = auth_client.post("/exercises", json=exercise_payload())

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == 1
    assert data["name"] == "Push Up"
    assert data["primary_muscles"] == ["chest"]


def test_reject_invalid_muscle_group(auth_client):
    response = auth_client.post("/exercises", json=exercise_payload(primary_muscles=["wings"]))

    assert response.status_code == 422


def test_reject_blank_name(auth_client):
    response = auth_client.post("/exercises", json=exercise_payload(name="   "))

    assert response.status_code == 422


def test_reject_empty_primary_muscles(auth_client):
    response = auth_client.post("/exercises", json=exercise_payload(primary_muscles=[]))

    assert response.status_code == 422


def test_reject_overlap_between_primary_and_secondary_muscles(auth_client):
    response = auth_client.post(
        "/exercises",
        json=exercise_payload(primary_muscles=["chest"], secondary_muscles=["chest"]),
    )

    assert response.status_code == 422


def test_reject_invalid_media_url(auth_client):
    response = auth_client.post("/exercises", json=exercise_payload(media_url="not-a-valid-url"))

    assert response.status_code == 422


def test_get_all_exercises(auth_client):
    auth_client.post("/exercises", json=exercise_payload())
    auth_client.post(
        "/exercises",
        json=exercise_payload(
            name="Squat",
            primary_muscles=["quadriceps"],
            secondary_muscles=["glutes", "hamstrings"],
        ),
    )
    response = auth_client.get("/exercises")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "Push Up"
    assert data[1]["name"] == "Squat"


def test_get_one_exercise_by_id(auth_client):
    create_response = auth_client.post("/exercises", json=exercise_payload())
    exercise_id = create_response.json()["id"]
    response = auth_client.get(f"/exercises/{exercise_id}")

    assert response.status_code == 200
    assert response.json()["name"] == "Push Up"


def test_return_404_for_non_existent_id(auth_client):
    response = auth_client.get("/exercises/999")

    assert response.status_code == 404
    assert response.json()["detail"] == NOT_FOUND_DETAIL


def test_list_exercises_is_public(client):
    response = client.get("/exercises")

    assert response.status_code == 200
    assert response.json() == []


def test_update_existing_exercise(auth_client):
    create_response = auth_client.post("/exercises", json=exercise_payload())
    exercise_id = create_response.json()["id"]
    response = auth_client.put(
        f"/exercises/{exercise_id}",
        json=exercise_payload(
            name="Incline Push Up",
            difficulty="intermediate",
            instructions="Place your hands on an elevated surface.",
        ),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == exercise_id
    assert data["name"] == "Incline Push Up"
    assert data["difficulty"] == "intermediate"


def test_update_non_existent_exercise(auth_client):
    response = auth_client.put("/exercises/999", json=exercise_payload(name="Updated Push Up"))

    assert response.status_code == 404
    assert response.json()["detail"] == NOT_FOUND_DETAIL


def test_delete_existing_exercise(auth_client):
    create_response = auth_client.post("/exercises", json=exercise_payload())
    exercise_id = create_response.json()["id"]
    delete_response = auth_client.delete(f"/exercises/{exercise_id}")
    get_response = auth_client.get(f"/exercises/{exercise_id}")

    assert delete_response.status_code == 204
    assert get_response.status_code == 404


def test_delete_same_exercise_twice_second_time_should_fail(auth_client):
    create_response = auth_client.post("/exercises", json=exercise_payload())
    exercise_id = create_response.json()["id"]
    first_delete = auth_client.delete(f"/exercises/{exercise_id}")
    second_delete = auth_client.delete(f"/exercises/{exercise_id}")

    assert first_delete.status_code == 204
    assert second_delete.status_code == 404
