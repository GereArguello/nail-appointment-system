from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from app.users.models import User
from app.users.schemas import UserRead


def test_postgres_engine(postgres_engine: Engine) -> None:
    assert postgres_engine.dialect.name == "postgresql"


def test_postgres_client_uses_database(
    client: TestClient,
    create_user: Callable[..., UserRead],
    postgres_engine: Engine,
) -> None:
    user = create_user()

    with Session(postgres_engine) as session:
        db_user = session.exec(select(User).where(User.id == user.id)).one()

    assert db_user.email == user.email
