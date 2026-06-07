from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.auth import create_access_token, hash_password
from app.db import get_session
from app.main import app
from app.models import UserTable

ALL_SCOPES = ["exercises:write", "history:read", "history:write", "coach:use"]
ATHLETE_SCOPES = ["history:read", "history:write", "coach:use"]


@pytest.fixture
def engine():
    # A single in-memory SQLite shared across sessions via StaticPool.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture
def db_session(engine) -> Iterator[Session]:
    with Session(engine) as session:
        yield session


@pytest.fixture
def client(engine) -> Iterator[TestClient]:
    def override_get_session() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    # Note: not entering TestClient as a context manager keeps the app's
    # lifespan (which seeds the real on-disk DB) from running during tests.
    yield TestClient(app)
    app.dependency_overrides.clear()


def _make_user(engine, username: str, scopes: list[str], role: str = "tester") -> str:
    with Session(engine) as session:
        session.add(
            UserTable(
                username=username,
                hashed_password=hash_password("secret"),
                role=role,
                scopes=scopes,
            )
        )
        session.commit()
    return create_access_token(username, scopes)


@pytest.fixture
def admin_token(engine) -> str:
    return _make_user(engine, "admin", ALL_SCOPES, role="admin")


@pytest.fixture
def athlete_token(engine) -> str:
    return _make_user(engine, "athlete", ATHLETE_SCOPES, role="athlete")


@pytest.fixture
def auth_client(client, admin_token) -> TestClient:
    client.headers.update({"Authorization": f"Bearer {admin_token}"})
    return client
