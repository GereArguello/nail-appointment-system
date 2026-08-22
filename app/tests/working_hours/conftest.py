from collections.abc import Callable
from datetime import timedelta
from typing import Any, cast

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.tests.factories import create_working_hours_data
from app.users.schemas import UserRead
from app.utils import utc_now
from app.working_hours.models import WorkingHour
from app.working_hours.schemas import WorkingHourRead


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
