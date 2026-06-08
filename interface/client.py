import os

import httpx

_BASE_URL = os.getenv("TRAINFLOW_API_URL", "http://localhost:8000")
_COACH_URL = os.getenv("TRAINFLOW_COACH_URL", "http://localhost:8001")


class BackendUnavailableError(Exception):
    pass


def _auth_headers(token: str | None) -> dict:
    return {"Authorization": f"Bearer {token}"} if token else {}


def login(username: str, password: str) -> str:
    """Return a JWT access token, or raise ValueError on bad credentials."""
    try:
        response = httpx.post(
            f"{_BASE_URL}/auth/token",
            data={"username": username, "password": password},
            timeout=5.0,
        )
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        raise BackendUnavailableError("Cannot connect to the backend") from exc
    if response.status_code == 200:
        return response.json()["access_token"]
    raise ValueError("Incorrect username or password")


def register(username: str, password: str) -> dict:
    """Create a new athlete account, or raise ValueError with the backend's
    message (e.g. username taken, weak password)."""
    try:
        response = httpx.post(
            f"{_BASE_URL}/auth/register",
            json={"username": username, "password": password},
            timeout=5.0,
        )
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        raise BackendUnavailableError("Cannot connect to the backend") from exc
    if response.is_success:
        return response.json()
    detail = response.json().get("detail", "Registration failed")
    raise ValueError(detail if isinstance(detail, str) else str(detail))


def get_me(token: str) -> dict:
    """Return the current user's profile ({username, role, scopes})."""
    try:
        response = httpx.get(f"{_BASE_URL}/auth/me", headers=_auth_headers(token), timeout=5.0)
        response.raise_for_status()
        return response.json()
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        raise BackendUnavailableError("Cannot connect to the backend") from exc


def list_exercises() -> list[dict]:
    try:
        response = httpx.get(f"{_BASE_URL}/exercises", timeout=5.0)
        response.raise_for_status()
        return response.json()
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        raise BackendUnavailableError("Cannot connect to the backend") from exc


def create_exercise(data: dict, token: str | None = None) -> dict:
    try:
        response = httpx.post(
            f"{_BASE_URL}/exercises",
            json=data,
            headers=_auth_headers(token),
            timeout=5.0,
        )
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        raise BackendUnavailableError("Cannot connect to the backend") from exc
    if not response.is_success:
        detail = response.json().get("detail", "Unknown error")
        raise ValueError(detail if isinstance(detail, str) else str(detail))
    return response.json()


def update_exercise(exercise_id: int, data: dict, token: str | None = None) -> dict:
    try:
        response = httpx.put(
            f"{_BASE_URL}/exercises/{exercise_id}",
            json=data,
            headers=_auth_headers(token),
            timeout=5.0,
        )
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        raise BackendUnavailableError("Cannot connect to the backend") from exc
    if not response.is_success:
        detail = response.json().get("detail", "Unknown error")
        raise ValueError(detail if isinstance(detail, str) else str(detail))
    return response.json()


def delete_exercise(exercise_id: int, token: str | None = None) -> None:
    try:
        response = httpx.delete(
            f"{_BASE_URL}/exercises/{exercise_id}",
            headers=_auth_headers(token),
            timeout=5.0,
        )
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        raise BackendUnavailableError("Cannot connect to the backend") from exc
    if response.status_code == 204:
        return
    detail = response.json().get("detail", "Unknown error") if response.content else "Delete failed"
    raise ValueError(detail if isinstance(detail, str) else str(detail))


def list_sessions(token: str, limit: int = 5) -> list[dict]:
    try:
        response = httpx.get(
            f"{_BASE_URL}/sessions",
            params={"limit": limit},
            headers=_auth_headers(token),
            timeout=5.0,
        )
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        raise BackendUnavailableError("Cannot connect to the backend") from exc
    if not response.is_success:
        return []
    return response.json()


def log_session(payload: dict, token: str) -> dict:
    try:
        response = httpx.post(
            f"{_BASE_URL}/sessions",
            json=payload,
            headers=_auth_headers(token),
            timeout=5.0,
        )
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        raise BackendUnavailableError("Cannot connect to the backend") from exc
    if not response.is_success:
        detail = response.json().get("detail", "Unknown error")
        raise ValueError(detail if isinstance(detail, str) else str(detail))
    return response.json()


def coach_status() -> str:
    """Return the coach provider (gemini | anthropic | fallback | unavailable)."""
    try:
        response = httpx.get(f"{_COACH_URL}/health", timeout=5.0)
    except (httpx.ConnectError, httpx.TimeoutException):
        return "unavailable"
    if response.is_success:
        return response.json().get("provider", "unknown")
    return "unavailable"


def request_plan(payload: dict, token: str) -> dict:
    try:
        response = httpx.post(
            f"{_COACH_URL}/plan",
            json=payload,
            headers=_auth_headers(token),
            timeout=60.0,
        )
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        raise BackendUnavailableError("Cannot connect to the coach service") from exc
    if not response.is_success:
        detail = response.json().get("detail", "Unknown error")
        raise ValueError(detail if isinstance(detail, str) else str(detail))
    return response.json()
