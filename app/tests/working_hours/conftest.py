from collections.abc import Callable
from datetime import timedelta
from typing import cast

import pytest
from sqlmodel import Session

from app.utils import utc_now
from app.working_hours.models import WorkingHour
from app.working_hours.schemas import WorkingHourRead


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
