from sqlmodel import Session, select

from app.models import Exercise, ExerciseInput, ExerciseTable


class ExerciseRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _to_schema(row: ExerciseTable) -> Exercise:
        return Exercise(
            id=row.id,
            name=row.name,
            primary_muscles=row.primary_muscles,
            secondary_muscles=row.secondary_muscles,
            equipment=row.equipment,
            difficulty=row.difficulty,
            instructions=row.instructions,
            media_url=row.media_url,
        )

    @staticmethod
    def _apply_input(row: ExerciseTable, data: ExerciseInput) -> ExerciseTable:
        payload = data.model_dump(mode="json")
        row.name = payload["name"]
        row.primary_muscles = payload["primary_muscles"]
        row.secondary_muscles = payload["secondary_muscles"]
        row.equipment = payload["equipment"]
        row.difficulty = payload["difficulty"]
        row.instructions = payload["instructions"]
        row.media_url = payload["media_url"]
        return row

    def list_all(self) -> list[Exercise]:
        rows = self._session.exec(select(ExerciseTable).order_by(ExerciseTable.id)).all()
        return [self._to_schema(row) for row in rows]

    def get(self, exercise_id: int) -> Exercise | None:
        row = self._session.get(ExerciseTable, exercise_id)
        return self._to_schema(row) if row is not None else None

    def create(self, exercise_data: ExerciseInput) -> Exercise:
        row = self._apply_input(ExerciseTable(), exercise_data)
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return self._to_schema(row)

    def update(self, exercise_id: int, exercise_data: ExerciseInput) -> Exercise | None:
        row = self._session.get(ExerciseTable, exercise_id)
        if row is None:
            return None
        self._apply_input(row, exercise_data)
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return self._to_schema(row)

    def delete(self, exercise_id: int) -> bool:
        row = self._session.get(ExerciseTable, exercise_id)
        if row is None:
            return False
        self._session.delete(row)
        self._session.commit()
        return True
