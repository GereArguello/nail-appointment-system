from collections.abc import Callable
from datetime import datetime, time, timedelta

import pytest

from app.appointments.schemas import AppointmentRead
from app.business_settings.schemas import BusinessSettingsRead
from app.calendar_blocks.schemas import CalendarBlockRead
from app.services.schemas import ServiceRead
from app.users.schemas import UserRead
from app.working_hours.schemas import WorkingHourRead


@pytest.fixture
def appointment(
    user_with_login: tuple[UserRead, str],
    create_business_settings: Callable[..., BusinessSettingsRead],
    create_service: Callable[..., ServiceRead],
    create_working_hours: Callable[..., WorkingHourRead],
    create_appointment: Callable[..., AppointmentRead],
) -> AppointmentRead:
    create_business_settings()
    service = create_service()
    working_hour = create_working_hours()

    user, _ = user_with_login

    return create_appointment(
        user_id=user.id,
        service=service,
        starts_at=datetime.combine(
            working_hour.date,
            working_hour.start_time,
        ),
    )


@pytest.fixture
def appointments(
    appointment_creation_setup: tuple[
        BusinessSettingsRead, ServiceRead, WorkingHourRead, datetime
    ],
    create_appointment: Callable[..., AppointmentRead],
    user_with_login: tuple[UserRead, str],
) -> list[AppointmentRead]:
    _, service, _, starts_at = appointment_creation_setup
    user, _ = user_with_login

    return [
        create_appointment(
            user_id=user.id,
            service=service,
            starts_at=starts_at + timedelta(days=i),
        )
        for i in range(5)
    ]


@pytest.fixture
def appointment_overlap_setup(
    appointment_creation_setup: tuple[
        BusinessSettingsRead, ServiceRead, WorkingHourRead, datetime
    ],
    create_appointment: Callable[..., AppointmentRead],
    user_with_login: tuple[UserRead, str],
) -> tuple[BusinessSettingsRead, ServiceRead, AppointmentRead, str]:
    business_settings, service, _, starts_at = appointment_creation_setup
    user, token = user_with_login

    starts_at += timedelta(hours=1)

    appointment = create_appointment(
        user_id=user.id,
        service=service,
        starts_at=starts_at,
    )

    return business_settings, service, appointment, token


@pytest.fixture
def appointment_overlap_context(
    create_business_settings: Callable[..., BusinessSettingsRead],
    create_working_hours: Callable[..., WorkingHourRead],
    user_with_login: tuple[UserRead, str],
) -> tuple[BusinessSettingsRead, WorkingHourRead, UserRead, str]:
    business_settings = create_business_settings()
    working_hour = create_working_hours()
    user, token = user_with_login

    return business_settings, working_hour, user, token


@pytest.fixture
def adjacent_appointment_setup(
    create_business_settings: Callable[..., BusinessSettingsRead],
    create_working_hours: Callable[..., WorkingHourRead],
    create_service: Callable[..., ServiceRead],
    user_with_login: tuple[UserRead, str],
) -> Callable[..., tuple[ServiceRead, datetime, UserRead, str]]:

    def _setup(
        start_offset_hours: int,
    ) -> tuple[ServiceRead, datetime, UserRead, str]:
        create_business_settings()
        working_hour = create_working_hours()

        service = create_service(
            duration_minutes=60,
            buffer_before_minutes=0,
            buffer_after_minutes=0,
        )

        existing_starts_at = datetime.combine(
            working_hour.date,
            working_hour.start_time,
        ) + timedelta(hours=start_offset_hours)

        user, token = user_with_login

        return service, existing_starts_at, user, token

    return _setup


@pytest.fixture
def calendar_block_setup(
    appointment_creation_setup: tuple[
        BusinessSettingsRead, ServiceRead, WorkingHourRead, datetime
    ],
    create_calendar_block: Callable[..., CalendarBlockRead],
) -> tuple[datetime, datetime]:
    _, _, working_hour, _ = appointment_creation_setup

    block_starts_at = datetime.combine(
        working_hour.date,
        time(hour=11),
    )
    block_ends_at = block_starts_at + timedelta(hours=1)

    create_calendar_block(
        starts_at=block_starts_at.isoformat(),
        ends_at=block_ends_at.isoformat(),
    )

    return block_starts_at, block_ends_at
