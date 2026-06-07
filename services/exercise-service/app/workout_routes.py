from fastapi import APIRouter, Depends, HTTPException, Query, Response, Security, status
from sqlmodel import Session

from app.auth import get_current_user
from app.db import get_session
from app.models import WorkoutSessionInput, WorkoutSessionRead
from app.workout_repository import WorkoutRepository

router = APIRouter(prefix="/sessions", tags=["history"])
NOT_FOUND_DETAIL = "Workout session not found"


def get_workout_repository(session: Session = Depends(get_session)) -> WorkoutRepository:
    return WorkoutRepository(session)


@router.post(
    "",
    response_model=WorkoutSessionRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Security(get_current_user, scopes=["history:write"])],
)
def create_session(
    data: WorkoutSessionInput,
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
    return repository.create_session(data)


@router.get(
    "",
    response_model=list[WorkoutSessionRead],
    dependencies=[Security(get_current_user, scopes=["history:read"])],
)
def list_sessions(
    limit: int = Query(default=10, ge=1, le=100),
    repository: WorkoutRepository = Depends(get_workout_repository),
) -> list[WorkoutSessionRead]:
    return repository.list_sessions(limit)


@router.get(
    "/{session_id}",
    response_model=WorkoutSessionRead,
    dependencies=[Security(get_current_user, scopes=["history:read"])],
)
def get_session_by_id(
    session_id: int,
    repository: WorkoutRepository = Depends(get_workout_repository),
) -> WorkoutSessionRead:
    session = repository.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND_DETAIL)
    return session


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Security(get_current_user, scopes=["history:write"])],
)
def delete_session(
    session_id: int,
    repository: WorkoutRepository = Depends(get_workout_repository),
) -> Response:
    if not repository.delete_session(session_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND_DETAIL)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
