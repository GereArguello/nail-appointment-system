from collections.abc import Callable
from datetime import date
from typing import cast

import pytest
from sqlmodel import Session

from app.business_settings.schemas import BusinessSettingsRead
from app.tests.helpers import get_local_date
from app.working_hours.models import WorkingHour
from app.working_hours.schemas import WorkingHourRead


@pytest.fixture
def create_working_hours_list(
    create_working_hours: Callable[..., WorkingHourRead],
    create_business_settings: Callable[..., BusinessSettingsRead],
) -> Callable[[int], list[WorkingHourRead]]:

    def _create_working_hours_list(amount: int) -> list[WorkingHourRead]:
        business_settings = create_business_settings()

        return [
            create_working_hours(
                date=get_local_date(
                    days_offset=i + 1,
                    timezone=business_settings.timezone,
                )
            )
            for i in range(amount)
        ]

    return _create_working_hours_list


@pytest.fixture
def create_past_working_hours(
    session: Session,
    create_working_hours: Callable[..., WorkingHourRead],
    create_business_settings: Callable[..., BusinessSettingsRead],
) -> Callable[[], WorkingHourRead]:

    def _create_past_working_hours() -> WorkingHourRead:
        business_settings = create_business_settings()

        created = create_working_hours()

        working_hour = session.get(WorkingHour, created.id)
        assert working_hour is not None

        working_hour.date = date.fromisoformat(
            get_local_date(
                days_offset=-1,
                timezone=business_settings.timezone,
            )
        )

        session.commit()
        session.refresh(working_hour)

        return cast(WorkingHourRead, WorkingHourRead.model_validate(working_hour))

    return _create_past_working_hours
