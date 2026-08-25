from collections.abc import Callable
from datetime import date, timedelta
from typing import cast

import pytest
from sqlmodel import Session, select

from app.calendar_blocks.models import CalendarBlock
from app.calendar_blocks.schemas import CalendarBlockRead
from app.tests.helpers import make_calendar_block_datetime
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
