from sqlmodel import Session, select

from app.models import (
    ExerciseTable,
    WorkoutExercise,
    WorkoutExerciseRead,
    WorkoutSession,
    WorkoutSessionInput,
    WorkoutSessionRead,
)


class WorkoutRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def catalog_has(self, exercise_id: int) -> bool:
        return self._session.get(ExerciseTable, exercise_id) is not None

    def _to_read(self, row: WorkoutSession) -> WorkoutSessionRead:
        children = self._session.exec(
            select(WorkoutExercise)
            .where(WorkoutExercise.session_id == row.id)
            .order_by(WorkoutExercise.id)
        ).all()
        exercises = []
        for child in children:
            catalog = self._session.get(ExerciseTable, child.exercise_id)
            exercises.append(
                WorkoutExerciseRead(
                    id=child.id,
                    exercise_id=child.exercise_id,
                    sets=child.sets,
                    reps=child.reps,
                    weight=child.weight,
                    exercise_name=catalog.name if catalog is not None else None,
                )
            )
        return WorkoutSessionRead(
            id=row.id,
            owner=row.owner,
            date=row.date,
            goal=row.goal,
            notes=row.notes,
            exercises=exercises,
        )

    def create_session(self, data: WorkoutSessionInput, owner: str | None = None) -> WorkoutSessionRead:
        session_row = WorkoutSession(
            owner=owner, date=data.date, goal=data.goal.value, notes=data.notes
        )
        self._session.add(session_row)
        self._session.flush()
        for item in data.exercises:
            self._session.add(
                WorkoutExercise(
                    session_id=session_row.id,
                    exercise_id=item.exercise_id,
                    sets=item.sets,
                    reps=item.reps,
                    weight=item.weight,
                )
            )
        self._session.commit()
        self._session.refresh(session_row)
        return self._to_read(session_row)

    def list_sessions(self, limit: int = 10, owner: str | None = None) -> list[WorkoutSessionRead]:
        statement = select(WorkoutSession)
        if owner is not None:
            statement = statement.where(WorkoutSession.owner == owner)
        statement = statement.order_by(
            WorkoutSession.date.desc(), WorkoutSession.id.desc()
        ).limit(limit)
        rows = self._session.exec(statement).all()
        return [self._to_read(row) for row in rows]

    def get_session(self, session_id: int, owner: str | None = None) -> WorkoutSessionRead | None:
        row = self._session.get(WorkoutSession, session_id)
        if row is None:
            return None
        if owner is not None and row.owner != owner:
            return None  # not the caller's session — hide its existence
        return self._to_read(row)

    def delete_session(self, session_id: int, owner: str | None = None) -> bool:
        row = self._session.get(WorkoutSession, session_id)
        if row is None:
            return False
        if owner is not None and row.owner != owner:
            return False
        children = self._session.exec(
            select(WorkoutExercise).where(WorkoutExercise.session_id == session_id)
        ).all()
        for child in children:
            self._session.delete(child)
        self._session.delete(row)
        self._session.commit()
        return True
