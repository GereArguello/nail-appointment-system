from collections.abc import Callable, Generator, Iterator
from typing import Any, cast

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel

import app.models as models  # noqa: F401
from app.business_settings.models import BusinessSettings
from app.business_settings.schemas import BusinessSettingsRead
from app.calendar_blocks.schemas import CalendarBlockRead
from app.core.database import get_session
from app.core.enums import RoleEnum
from app.main import app
from app.tests.factories import (
    create_business_settings_data,
    create_calendar_block_data,
    create_data,
    create_working_hours_data,
)
from app.tests.helpers import ensure_working_hour
from app.users.models import User
from app.users.schemas import UserRead
from app.utils import parse_as_utc
from app.working_hours.schemas import WorkingHourRead

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
) -> Callable[..., UserRead]:

    def _create_user(**overrides: Any) -> UserRead:
        data = create_data(**overrides)

        response = client.post("/users/", json=data)
        assert response.status_code == status.HTTP_201_CREATED

        response_data: dict[str, Any] = response.json()

        return cast(UserRead, UserRead.model_validate(response_data))

    return _create_user


@pytest.fixture
def user_with_login(
    client: TestClient, create_user: Callable[..., UserRead]
) -> tuple[UserRead, str]:
    user = create_user()

    response = client.post(
        "/auth/login", data={"username": user.email, "password": "A12345678"}
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    return user, data["access_token"]


@pytest.fixture
def admin_with_login(
    client: TestClient, session: Session, create_user: Callable[..., UserRead]
) -> tuple[UserRead, str]:
    user = create_user(first_name="admin", email="admin@gmail.com")

    db_user = session.get(User, user.id)

    assert db_user is not None

    db_user.role = RoleEnum.ADMIN

    session.commit()
    session.refresh(db_user)

    response = client.post(
        "/auth/login",
        data={
            "username": db_user.email,
            "password": "A12345678",
        },
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    admin = UserRead.model_validate(db_user)

    return admin, data["access_token"]


@pytest.fixture
def create_working_hours(
    client: TestClient, admin_with_login: tuple[UserRead, str]
) -> Callable[..., WorkingHourRead]:

    def _create_working_hours(**overrides: Any) -> WorkingHourRead:
        _, token = admin_with_login
        data = create_working_hours_data(**overrides)

        response = client.post(
            "/working-hours/", json=data, headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == status.HTTP_201_CREATED

        response_data: dict[str, Any] = response.json()

        return cast(WorkingHourRead, WorkingHourRead.model_validate(response_data))

    return _create_working_hours


@pytest.fixture
def create_calendar_block(
    client: TestClient,
    session: Session,
    admin_with_login: tuple[UserRead, str],
    create_working_hours: Callable[..., WorkingHourRead],
) -> Callable[..., CalendarBlockRead]:

    def _create_calendar_block(**overrides: Any) -> CalendarBlockRead:
        _, token = admin_with_login
        data = create_calendar_block_data(**overrides)

        starts_at = parse_as_utc(data["starts_at"])

        ensure_working_hour(
            session,
            create_working_hours,
            starts_at.date(),
        )

        response = client.post(
            "/calendar-blocks/",
            json=data,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_201_CREATED, response.json()

        return cast(
            CalendarBlockRead, CalendarBlockRead.model_validate(response.json())
        )

    return _create_calendar_block


@pytest.fixture
def create_business_settings(
    session: Session,
) -> Callable[..., BusinessSettingsRead]:
    def _create_business_settings(**overrides: Any) -> BusinessSettingsRead:
        data = create_business_settings_data(**overrides)

        business_settings = BusinessSettings(**data)

        session.add(business_settings)
        session.commit()
        session.refresh(business_settings)

        return cast(
            BusinessSettingsRead, BusinessSettingsRead.model_validate(business_settings)
        )

    return _create_business_settings
