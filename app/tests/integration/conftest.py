from collections.abc import Generator, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings
from app.core.database import get_session
from app.main import app


@pytest.fixture
def postgres_engine() -> Generator[Engine]:
    database_url = settings.TEST_DATABASE_URL

    if database_url is None:
        raise RuntimeError("TEST_DATABASE_URL no está configurada")

    engine = create_engine(database_url)

    try:
        # Verificar la base de datos real
        with engine.connect() as connection:
            database_name = connection.execute(
                text("SELECT current_database()")
            ).scalar_one()

        if database_name != "manicura_test":
            raise RuntimeError("La conexión no apunta a manicura_test")

        SQLModel.metadata.create_all(engine)

        try:
            yield engine
        finally:
            SQLModel.metadata.drop_all(engine)

    finally:
        engine.dispose()


@pytest.fixture
def postgres_client(postgres_engine: Engine) -> Generator[TestClient]:
    def get_test_session() -> Iterator[Session]:
        with Session(postgres_engine) as session:
            yield session

    app.dependency_overrides[get_session] = get_test_session

    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.fixture
def client(postgres_client: TestClient) -> TestClient:
    return postgres_client


@pytest.fixture
def session(postgres_engine: Engine) -> Generator[Session]:
    with Session(postgres_engine) as session:
        yield session
