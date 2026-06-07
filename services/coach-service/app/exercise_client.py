import os

import httpx

from app.schemas import CatalogExercise

EXERCISE_API_URL = os.getenv("EXERCISE_API_URL", "http://localhost:8000")


class ExerciseServiceError(Exception):
    pass


class ExerciseClient:
    """Reads catalog and history from exercise-service over HTTP, forwarding the
    caller's JWT. The coach never touches the database directly."""

    def __init__(self, token: str, base_url: str = EXERCISE_API_URL) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {token}"}

    def get_catalog(self) -> list[CatalogExercise]:
        try:
            response = httpx.get(f"{self._base_url}/exercises", timeout=10.0)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ExerciseServiceError("Could not fetch catalog") from exc
        return [CatalogExercise.model_validate(item) for item in response.json()]

    def get_history(self, limit: int) -> list[dict]:
        """Best-effort: history is additive. If the caller lacks the history
        scope or the service is unavailable, return an empty list and plan from
        preferences only."""
        if limit <= 0:
            return []
        try:
            response = httpx.get(
                f"{self._base_url}/sessions",
                params={"limit": limit},
                headers=self._headers,
                timeout=10.0,
            )
        except httpx.HTTPError:
            return []
        if response.status_code in (401, 403) or not response.is_success:
            return []
        return response.json()
