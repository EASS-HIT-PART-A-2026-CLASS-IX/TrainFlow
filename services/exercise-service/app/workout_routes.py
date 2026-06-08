from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlmodel import Session

from app.auth import is_admin, require_history_read, require_history_write
from app.db import get_session
from app.models import UserTable, WorkoutSessionInput, WorkoutSessionRead
from app.workout_repository import WorkoutRepository

router = APIRouter(prefix="/sessions", tags=["history"])
NOT_FOUND_DETAIL = "Workout session not found"


def get_workout_repository(session: Session = Depends(get_session)) -> WorkoutRepository:
    return WorkoutRepository(session)


def _owner_filter(user: UserTable) -> str | None:
    """Admins see everyone's history (None = no filter); athletes see only their own."""
    return None if is_admin(user) else user.username


@router.post(
    "",
    response_model=WorkoutSessionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_session(
    data: WorkoutSessionInput,
    user: UserTable = Depends(require_history_write),
    repository: WorkoutRepository = Depends(get_workout_repository),
) -> WorkoutSessionRead:
    unknown = sorted(
        {item.exercise_id for item in data.exercises if not repository.catalog_has(item.exercise_id)}
    )
    if unknown:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown exercise_id(s) not in catalog: {unknown}",
        )
    return repository.create_session(data, owner=user.username)


@router.get("", response_model=list[WorkoutSessionRead])
def list_sessions(
    limit: int = Query(default=10, ge=1, le=100),
    user: UserTable = Depends(require_history_read),
    repository: WorkoutRepository = Depends(get_workout_repository),
) -> list[WorkoutSessionRead]:
    return repository.list_sessions(limit, owner=_owner_filter(user))


@router.get("/{session_id}", response_model=WorkoutSessionRead)
def get_session_by_id(
    session_id: int,
    user: UserTable = Depends(require_history_read),
    repository: WorkoutRepository = Depends(get_workout_repository),
) -> WorkoutSessionRead:
    session = repository.get_session(session_id, owner=_owner_filter(user))
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND_DETAIL)
    return session


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: int,
    user: UserTable = Depends(require_history_write),
    repository: WorkoutRepository = Depends(get_workout_repository),
) -> Response:
    if not repository.delete_session(session_id, owner=_owner_filter(user)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND_DETAIL)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
