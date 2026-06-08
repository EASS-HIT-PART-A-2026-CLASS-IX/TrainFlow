from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import require_coach
from app.exercise_client import ExerciseClient, ExerciseServiceError
from app.planner.context import build_context
from app.planner.factory import active_provider, get_planner
from app.schemas import PlanRequest, WorkoutPlan

router = APIRouter(tags=["coach"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "provider": active_provider()}


@router.post("/plan", response_model=WorkoutPlan)
def create_plan(
    request: PlanRequest,
    token: str = Depends(require_coach),
) -> WorkoutPlan:
    client = ExerciseClient(token)
    try:
        catalog = client.get_catalog()
    except ExerciseServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Exercise catalog is unavailable",
        ) from exc

    if not catalog:
        raise HTTPException(
            status_code=422,
            detail="Exercise catalog is empty; add exercises before planning",
        )

    history = client.get_history(request.history_limit)
    context = build_context(history, catalog)
    planner = get_planner()
    return planner.generate(request, catalog, context)
