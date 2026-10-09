from collections.abc import Callable
from datetime import datetime, time
from zoneinfo import ZoneInfo

from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.appointments.service import calculate_first_and_last_possible_start
from app.business_settings.schemas import BusinessSettingsRead
from app.calendar_blocks.schemas import CalendarBlockRead
from app.services.schemas import ServiceRead
from app.working_hours.schemas import WorkingHourRead


def test_should_calculate_first_and_last_possible_start(
    session: Session,
    create_working_hours: Callable[..., WorkingHourRead],
    create_service: Callable[..., ServiceRead],
    create_business_settings: Callable[..., BusinessSettingsRead],
) -> None:
    business_settings = create_business_settings(
        appointment_start_tolerance_minutes=5,
        appointment_end_tolerance_minutes=10,
    )

    working_hour = create_working_hours(
        start_time="09:00:00",
        end_time="18:00:00",
    )

    service = create_service(
        duration_minutes=60,
        buffer_before_minutes=10,
        buffer_after_minutes=15,
    )

    first, last = calculate_first_and_last_possible_start(
        working_hour, service, business_settings
    )

    timezone = ZoneInfo(business_settings.timezone)

    expected_first = datetime.combine(working_hour.date, time(9, 5), tzinfo=timezone)

    expected_last = datetime.combine(working_hour.date, time(16, 55), tzinfo=timezone)

    assert first == expected_first
    assert last == expected_last


def test_should_return_404_if_date_has_no_working_hour(
    client: TestClient,
    create_service: Callable[..., ServiceRead],
) -> None:
    service = create_service()

    response = client.get(
        "/appointments/availability",
        params={
            "target_date": "2026-09-21",
            "service_id": service.id,
        },
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Esta fecha no tiene horario laborable"


def test_should_return_404_if_service_not_exists(
    client: TestClient,
    create_working_hours: Callable[..., WorkingHourRead],
) -> None:
    working_hour = create_working_hours()

    response = client.get(
        "/appointments/availability",
        params={
            "target_date": working_hour.date,
            "service_id": 999,
        },
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Servicio no encontrado"


def test_should_return_409_if_service_does_not_fit_working_hours(
    client: TestClient,
    create_working_hours: Callable[..., WorkingHourRead],
    create_service: Callable[..., ServiceRead],
    create_business_settings: Callable[..., BusinessSettingsRead],
) -> None:
    create_business_settings(
        appointment_start_tolerance_minutes=0,
        appointment_end_tolerance_minutes=0,
    )

    working_hour = create_working_hours(start_time="17:00:00", end_time="18:00:00")
    service = create_service(
        duration_minutes=60,
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

    assert response.status_code == status.HTTP_409_CONFLICT
    assert (
        response.json()["detail"]
        == "El servicio no entra dentro del horario laboral disponible"
    )


def test_should_return_all_available_slots_when_day_is_empty(
    client: TestClient,
    create_business_settings: Callable[..., BusinessSettingsRead],
    create_working_hours: Callable[..., WorkingHourRead],
    create_service: Callable[..., ServiceRead],
) -> None:
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


def test_should_return_empty_list_if_no_slots_are_available(
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
        end_time="10:00:00",
    )

    service = create_service(
        duration_minutes=30,
        buffer_before_minutes=0,
        buffer_after_minutes=0,
    )

    create_calendar_block(
        starts_at=f"{working_hour.date}T09:00:00",
        ends_at=f"{working_hour.date}T10:00:00",
    )

    response = client.get(
        "/appointments/availability",
        params={
            "target_date": working_hour.date,
            "service_id": service.id,
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []
