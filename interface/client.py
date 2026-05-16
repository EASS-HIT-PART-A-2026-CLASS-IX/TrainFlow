import os

import httpx

_BASE_URL = os.getenv("TRAINFLOW_API_URL", "http://localhost:8000")


class BackendUnavailableError(Exception):
    pass


def list_exercises() -> list[dict]:
    try:
        response = httpx.get(f"{_BASE_URL}/exercises", timeout=5.0)
        response.raise_for_status()
        return response.json()
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        raise BackendUnavailableError("Cannot connect to the backend") from exc


def create_exercise(data: dict) -> dict:
    try:
        response = httpx.post(f"{_BASE_URL}/exercises", json=data, timeout=5.0)
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        raise BackendUnavailableError("Cannot connect to the backend") from exc
    if not response.is_success:
        detail = response.json().get("detail", "Unknown error")
        raise ValueError(detail if isinstance(detail, str) else str(detail))
    return response.json()
