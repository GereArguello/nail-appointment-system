from collections.abc import Callable

from fastapi import status
from fastapi.testclient import TestClient

from app.business_settings.schemas import BusinessSettingsRead
from app.calendar_blocks.schemas import CalendarBlockRead
from app.services.schemas import ServiceRead
from app.working_hours.schemas import WorkingHourRead


def test_should_exclude_slots_overlapping_calendar_block(
    client: TestClient,
    create_business_settings: Callable[..., BusinessSettingsRead],
    create_working_hours: Callable[..., WorkingHourRead],
    create_service: Callable[..., ServiceRead],
    create_calendar_block: Callable[..., CalendarBlockRead],
) -> None:
    create_business_settings(
        appointment_start_tolerance_minutes=0,
        appointment_end_tolerance_minutes=0,
    )

    working_hour = create_working_hours(
        start_time="09:00:00",
        end_time="12:00:00",
    )

    create_calendar_block(
        starts_at=f"{working_hour.date}T10:30:00",
        ends_at=f"{working_hour.date}T11:30:00",
    )

    service = create_service(
        duration_minutes=30,
        buffer_before_minutes=0,
        buffer_after_minutes=0,
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
        f"{working_hour.date}T09:45:00",
        f"{working_hour.date}T10:00:00",
        f"{working_hour.date}T11:30:00",
    ]


def test_should_exclude_slots_overlapping_calendar_block_with_service_buffers(
    client: TestClient,
    create_business_settings: Callable[..., BusinessSettingsRead],
    create_working_hours: Callable[..., WorkingHourRead],
    create_service: Callable[..., ServiceRead],
    create_calendar_block: Callable[..., CalendarBlockRead],
) -> None:
    create_business_settings(
        appointment_start_tolerance_minutes=0,
        appointment_end_tolerance_minutes=0,
    )

    working_hour = create_working_hours(
        start_time="09:00:00",
        end_time="12:00:00",
    )

    create_calendar_block(
        starts_at=f"{working_hour.date}T10:30:00",
        ends_at=f"{working_hour.date}T11:00:00",
    )

    service = create_service(
        duration_minutes=30,
        buffer_before_minutes=10,
        buffer_after_minutes=10,
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
        f"{working_hour.date}T09:10:00",
        f"{working_hour.date}T09:25:00",
        f"{working_hour.date}T09:40:00",
        f"{working_hour.date}T11:10:00",
    ]
