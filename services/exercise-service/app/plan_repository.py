from sqlmodel import Session, select

from app.models import PlanRecordInput, PlanRecordRead, WorkoutPlanRecord


class PlanRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _to_read(row: WorkoutPlanRecord) -> PlanRecordRead:
        return PlanRecordRead(
            id=row.id,
            owner=row.owner,
            created_at=row.created_at,
            goal=row.goal,
            generated_by=row.generated_by,
            request=row.request_json,
            plan=row.plan_json,
        )

    def save(self, data: PlanRecordInput, owner: str) -> PlanRecordRead:
        row = WorkoutPlanRecord(
            owner=owner,
            goal=data.goal,
            generated_by=data.generated_by,
            request_json=data.request,
            plan_json=data.plan,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return self._to_read(row)

    def latest(self, owner: str) -> PlanRecordRead | None:
        row = self._session.exec(
            select(WorkoutPlanRecord)
            .where(WorkoutPlanRecord.owner == owner)
            .order_by(WorkoutPlanRecord.created_at.desc(), WorkoutPlanRecord.id.desc())
        ).first()
        return self._to_read(row) if row is not None else None

    def list_for_owner(self, owner: str, limit: int = 10) -> list[PlanRecordRead]:
        rows = self._session.exec(
            select(WorkoutPlanRecord)
            .where(WorkoutPlanRecord.owner == owner)
            .order_by(WorkoutPlanRecord.created_at.desc(), WorkoutPlanRecord.id.desc())
            .limit(limit)
        ).all()
        return [self._to_read(row) for row in rows]
