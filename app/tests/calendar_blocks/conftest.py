from collections.abc import Callable
from datetime import date, timedelta
from typing import Any, cast

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.calendar_blocks.models import CalendarBlock
from app.calendar_blocks.schemas import CalendarBlockRead
from app.tests.calendar_blocks.helpers import make_calendar_block_datetime, parse_as_utc
from app.tests.factories import create_calendar_block_data
from app.users.schemas import UserRead
from app.utils import utc_now
from app.working_hours.models import WorkingHour
from app.working_hours.schemas import WorkingHourRead


def ensure_working_hour(
    session: Session,
    create_working_hours: Callable[..., WorkingHourRead],
    date: date,
) -> None:
    existing = session.exec(select(WorkingHour).where(WorkingHour.date == date)).first()

    if existing is None:
        create_working_hours(
            date=date.isoformat(),
            start_time="09:00:00",
            end_time="18:00:00",
        )


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
def create_calendar_block_list(
    create_calendar_block: Callable[..., CalendarBlockRead],
) -> Callable[[int], list[CalendarBlockRead]]:
    def _create_calendar_block_list(amount: int) -> list[CalendarBlockRead]:
        return [
            create_calendar_block(
                starts_at=make_calendar_block_datetime(days=i + 1, hour=13),
                ends_at=make_calendar_block_datetime(days=i + 1, hour=15),
            )
            for i in range(amount)
        ]

    return _create_calendar_block_list


@pytest.fixture
def create_past_calendar_block(
    session: Session,
    create_calendar_block: Callable[..., CalendarBlockRead],
) -> Callable[..., CalendarBlockRead]:
    def _create_past_calendar_block() -> CalendarBlockRead:
        created = create_calendar_block(
            starts_at=make_calendar_block_datetime(days=10, hour=13),
            ends_at=make_calendar_block_datetime(days=10, hour=14),
        )

        calendar_block = session.get(CalendarBlock, created.id)

        assert calendar_block is not None

        calendar_block.starts_at = utc_now() - timedelta(days=2)
        calendar_block.ends_at = utc_now() - timedelta(days=1)

        session.commit()
        session.refresh(calendar_block)

        return cast(CalendarBlockRead, CalendarBlockRead.model_validate(calendar_block))

    return _create_past_calendar_block
