from collections.abc import Callable
from datetime import datetime

import pytest

from app.appointments.schemas import AppointmentRead
from app.business_settings.schemas import BusinessSettingsRead
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
