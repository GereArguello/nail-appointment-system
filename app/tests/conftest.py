from collections.abc import Callable, Generator, Iterator
from datetime import timedelta
from typing import Any, cast

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel

from app.calendar_blocks.schemas import CalendarBlockRead
from app.core.database import get_session
from app.core.enums import RoleEnum, StatusEnum
from app.main import app
from app.services.models import Service
from app.services.schemas import ServiceRead
from app.tests.factories import (
    create_calendar_block_data,
    create_data,
    create_service_data,
    create_working_hours_data,
)
from app.users.models import User
from app.users.schemas import UserRead
from app.utils import utc_now
from app.working_hours.models import WorkingHour
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
def create_service(
    client: TestClient,
    admin_with_login: tuple[UserRead, str],
) -> Callable[..., ServiceRead]:
    _, token = admin_with_login

    def _create_service(**overrides: Any) -> ServiceRead:
        data = create_service_data(**overrides)

        response = client.post(
            "/services/",
            json=data,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_201_CREATED

        return cast(UserRead, ServiceRead.model_validate(response.json()))

    return _create_service


@pytest.fixture
def inactive_service(
    session: Session, create_service: Callable[..., ServiceRead]
) -> ServiceRead:
    service = create_service(name="Manicura clásica 2")

    service_db = session.get(Service, service.id)

    assert service_db is not None

    service_db.status = StatusEnum.INACTIVE

    session.commit()
    session.refresh(service_db)

    inactive_service: ServiceRead = ServiceRead.model_validate(service_db)
    return inactive_service


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
def create_working_hours_list(
    create_working_hours: Callable[..., WorkingHourRead],
) -> Callable[[int], list[WorkingHourRead]]:

    def _create_working_hours_list(amount: int) -> list[WorkingHourRead]:
        return [
            create_working_hours(
                date=(utc_now() + timedelta(days=i + 1)).date().isoformat()
            )
            for i in range(amount)
        ]

    return _create_working_hours_list


@pytest.fixture
def create_past_working_hours(
    session: Session,
    create_working_hours: Callable[..., WorkingHourRead],
) -> Callable[..., WorkingHour]:
    def _create_past_working_hours() -> WorkingHourRead:
        created = create_working_hours()

        working_hour = session.get(WorkingHour, created.id)

        assert working_hour is not None

        working_hour.date = (utc_now() - timedelta(days=1)).date()

        session.commit()
        session.refresh(working_hour)

        return cast(WorkingHourRead, WorkingHourRead.model_validate(working_hour))

    return _create_past_working_hours


@pytest.fixture
def create_calendar_block(
    client: TestClient, admin_with_login: tuple[UserRead, str]
) -> Callable[..., CalendarBlockRead]:
    def _create_calendar_block(**overrides: Any) -> CalendarBlockRead:

        _, token = admin_with_login
        data = create_calendar_block_data(**overrides)

        response = client.post(
            "/calendar-blocks/",
            json=data,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_201_CREATED

        response_data: dict[str, Any] = response.json()

        return cast(CalendarBlockRead, CalendarBlockRead.model_validate(response_data))

    return _create_calendar_block
