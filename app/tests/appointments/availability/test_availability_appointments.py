from collections.abc import Callable
from datetime import datetime, time, timedelta

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.appointments.schemas import AppointmentRead
from app.business_settings.schemas import BusinessSettingsRead
from app.core.enums import AppointmentStatusEnum
from app.services.schemas import ServiceRead
from app.users.schemas import UserRead
from app.working_hours.schemas import WorkingHourRead


def test_should_exclude_slots_overlapping_appointment(
    client: TestClient,
    create_business_settings: Callable[..., BusinessSettingsRead],
    create_working_hours: Callable[..., WorkingHourRead],
    create_service: Callable[..., ServiceRead],
    create_appointment: Callable[..., AppointmentRead],
    user_with_login: tuple[UserRead, str],
) -> None:
    user, _ = user_with_login

    create_business_settings(
        appointment_start_tolerance_minutes=0,
        appointment_end_tolerance_minutes=0,
    )

    working_hour = create_working_hours(
        start_time="09:00:00",
        end_time="12:00:00",
    )

    service = create_service(
        duration_minutes=60,
        buffer_before_minutes=0,
        buffer_after_minutes=0,
    )

    create_appointment(
        user_id=user.id,
        service=service,
        starts_at=(
            datetime.combine(
                working_hour.date,
                working_hour.start_time,
            )
            + timedelta(hours=1, minutes=30)
        ),
    )

    response = client.get(
        "/appointments/availability",
        params={
            "target_date": working_hour.date,
            "service_id": service.id,
        },
    )

    assert response.status_code == status.HTTP_200_OK

    assert response.json() == [
        f"{working_hour.date}T09:00:00",
        f"{working_hour.date}T09:15:00",
        f"{working_hour.date}T09:30:00",
    ]


def test_should_exclude_slots_overlapping_appointment_with_existing_service_buffers(
    client: TestClient,
    create_business_settings: Callable[..., BusinessSettingsRead],
    create_working_hours: Callable[..., WorkingHourRead],
    create_service: Callable[..., ServiceRead],
    create_appointment: Callable[..., AppointmentRead],
    user_with_login: tuple[UserRead, str],
) -> None:
    user, _ = user_with_login

    create_business_settings(
        appointment_start_tolerance_minutes=0,
        appointment_end_tolerance_minutes=0,
    )

    working_hour = create_working_hours(
        start_time="09:00:00",
        end_time="12:00:00",
    )

    existing_service = create_service(
        name="Servicio existente",
        duration_minutes=30,
        buffer_before_minutes=10,
        buffer_after_minutes=10,
    )

    requested_service = create_service(
        name="Servicio solicitado",
        duration_minutes=30,
        buffer_before_minutes=0,
        buffer_after_minutes=0,
    )

    create_appointment(
        user_id=user.id,
        service=existing_service,
        starts_at=(
            datetime.combine(
                working_hour.date,
                working_hour.start_time,
            )
            + timedelta(hours=1, minutes=30)
        ),
    )

    response = client.get(
        "/appointments/availability",
        params={
            "target_date": working_hour.date,
            "service_id": requested_service.id,
        },
    )

    assert response.status_code == status.HTTP_200_OK

    assert response.json() == [
        f"{working_hour.date}T09:00:00",
        f"{working_hour.date}T09:15:00",
        f"{working_hour.date}T09:30:00",
        f"{working_hour.date}T09:45:00",
        f"{working_hour.date}T11:15:00",
        f"{working_hour.date}T11:30:00",
    ]


@pytest.mark.parametrize(
    "appointment_status",
    [
        AppointmentStatusEnum.CANCELLED_BY_CLIENT,
        AppointmentStatusEnum.CANCELLED_BY_ADMIN,
        AppointmentStatusEnum.NO_SHOW,
    ],
)
def test_should_not_exclude_slots_for_non_occupying_appointment_status(
    client: TestClient,
    create_business_settings: Callable[..., BusinessSettingsRead],
    create_working_hours: Callable[..., WorkingHourRead],
    create_service: Callable[..., ServiceRead],
    create_appointment: Callable[..., AppointmentRead],
    user_with_login: tuple[UserRead, str],
    appointment_status: AppointmentStatusEnum,
) -> None:
    user, _ = user_with_login

    create_business_settings(
        appointment_start_tolerance_minutes=0,
        appointment_end_tolerance_minutes=0,
    )

    working_hour = create_working_hours(
        start_time="09:00:00",
        end_time="10:00:00",
    )

    service = create_service(
        duration_minutes=30,
        buffer_before_minutes=0,
        buffer_after_minutes=0,
    )

    create_appointment(
        user_id=user.id,
        service=service,
        starts_at=datetime.combine(
            working_hour.date,
            time(9, 15),
        ),
        status=appointment_status,
    )

    response = client.get(
        "/appointments/availability",
        params={
            "target_date": working_hour.date,
            "service_id": service.id,
        },
    )

    assert response.status_code == status.HTTP_200_OK

    assert response.json() == [
        f"{working_hour.date}T09:00:00",
        f"{working_hour.date}T09:15:00",
        f"{working_hour.date}T09:30:00",
    ]
