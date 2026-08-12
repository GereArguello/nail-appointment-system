from collections.abc import Callable, Generator, Iterator
from typing import Any, cast

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel

from app.core.database import get_session
from app.main import app
from app.tests.factories import create_data
from app.users.schemas import UserRead

sqlite_url = "sqlite:///:memory:"

engine = create_engine(
    sqlite_url, connect_args={"check_same_thread": False}, poolclass=StaticPool
)


@pytest.fixture(name="session")
def session_fixture() -> Generator[Session]:
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="client")
def client_fixture(session: Session) -> Generator[TestClient]:
    def get_session_override() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def create_user(
    client: TestClient,
) -> Callable[[], UserRead]:

    def _create_user(**overrides: Any) -> UserRead:
        data = create_data(**overrides)

        response = client.post("/users/", json=data)
        assert response.status_code == status.HTTP_201_CREATED

        response_data: dict[str, Any] = response.json()

        return cast(UserRead, UserRead.model_validate(response_data))

    return _create_user
