from fastapi import APIRouter, Depends, HTTPException, Response, Security, status
from sqlmodel import Session

from app.auth import get_current_user
from app.db import get_session
from app.models import Exercise, ExerciseInput
from app.repository import ExerciseRepository

router = APIRouter(prefix="/exercises", tags=["exercises"])
NOT_FOUND_DETAIL = "Exercise not found"


def get_repository(session: Session = Depends(get_session)) -> ExerciseRepository:
    return ExerciseRepository(session)


@router.post(
    "",
    response_model=Exercise,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Security(get_current_user, scopes=["exercises:write"])],
)
def create_exercise(
    exercise_data: ExerciseInput,
    repository: ExerciseRepository = Depends(get_repository),
) -> Exercise:
    return repository.create(exercise_data)


@router.get("", response_model=list[Exercise])
def list_exercises(
    repository: ExerciseRepository = Depends(get_repository),
) -> list[Exercise]:
    return repository.list_all()


@router.get("/{exercise_id}", response_model=Exercise)
def get_exercise(
    exercise_id: int,
    repository: ExerciseRepository = Depends(get_repository),
) -> Exercise:
    exercise = repository.get(exercise_id)
    if exercise is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND_DETAIL)
    return exercise


@router.put(
    "/{exercise_id}",
    response_model=Exercise,
    dependencies=[Security(get_current_user, scopes=["exercises:write"])],
)
def update_exercise(
    exercise_id: int,
    exercise_data: ExerciseInput,
    repository: ExerciseRepository = Depends(get_repository),
) -> Exercise:
    exercise = repository.update(exercise_id, exercise_data)
    if exercise is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND_DETAIL)
    return exercise


@router.delete(
    "/{exercise_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Security(get_current_user, scopes=["exercises:write"])],
)
def delete_exercise(
    exercise_id: int,
    repository: ExerciseRepository = Depends(get_repository),
) -> Response:
    deleted = repository.delete(exercise_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND_DETAIL)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
