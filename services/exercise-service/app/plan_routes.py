from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.auth import require_scopes
from app.db import get_session
from app.models import PlanRecordInput, PlanRecordRead, UserTable
from app.plan_repository import PlanRepository

router = APIRouter(prefix="/plans", tags=["plans"])

# Saving and reading generated plans needs the coach scope, which both athletes
# and admins hold. Plans are always scoped to the owner (the JWT subject).
require_coach = require_scopes("coach:use")


def get_plan_repository(session: Session = Depends(get_session)) -> PlanRepository:
    return PlanRepository(session)


@router.post("", response_model=PlanRecordRead, status_code=status.HTTP_201_CREATED)
def save_plan(
    data: PlanRecordInput,
    user: UserTable = Depends(require_coach),
    repository: PlanRepository = Depends(get_plan_repository),
) -> PlanRecordRead:
    return repository.save(data, owner=user.username)


@router.get("/latest", response_model=PlanRecordRead)
def latest_plan(
    user: UserTable = Depends(require_coach),
    repository: PlanRepository = Depends(get_plan_repository),
) -> PlanRecordRead:
    plan = repository.latest(user.username)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No saved plan")
    return plan


@router.get("", response_model=list[PlanRecordRead])
def list_plans(
    limit: int = Query(default=10, ge=1, le=50),
    user: UserTable = Depends(require_coach),
    repository: PlanRepository = Depends(get_plan_repository),
) -> list[PlanRecordRead]:
    return repository.list_for_owner(user.username, limit)
