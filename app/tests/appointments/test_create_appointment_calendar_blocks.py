from collections.abc import Callable
from datetime import UTC, datetime, time, timedelta

from fastapi import status
from fastapi.testclient import TestClient

from app.business_settings.schemas import BusinessSettingsRead
from app.calendar_blocks.schemas import CalendarBlockRead
from app.services.schemas import ServiceRead
from app.users.schemas import UserRead
from app.working_hours.schemas import WorkingHourRead


def test_should_fail_if_appointment_overlaps_calendar_block(
    client: TestClient,
    create_business_settings: Callable[..., BusinessSettingsRead],
    create_working_hours: Callable[..., WorkingHourRead],
    create_calendar_block: Callable[..., CalendarBlockRead],
    create_service: Callable[..., ServiceRead],
    user_with_login: tuple[UserRead, str],
) -> None:
    create_business_settings()
    working_hour = create_working_hours()
    service = create_service()

    starts_at = datetime.combine(
        working_hour.date,
        working_hour.start_time,
        tzinfo=UTC,
    )

    create_calendar_block(
        starts_at=starts_at.isoformat(),
        ends_at=(starts_at + timedelta(hours=1)).isoformat(),
    )

    _, token = user_with_login

    response = client.post(
        "/appointments/",
        json={
            "service_id": service.id,
            "starts_at": starts_at.isoformat(),
            "description": "Diseño francés con detalles dorados",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == "Horario bloqueado por el administrador"


def test_should_fail_if_appointment_partially_overlaps_calendar_block(
    client: TestClient,
    create_business_settings: Callable[..., BusinessSettingsRead],
    create_working_hours: Callable[..., WorkingHourRead],
    create_calendar_block: Callable[..., CalendarBlockRead],
    create_service: Callable[..., ServiceRead],
    user_with_login: tuple[UserRead, str],
) -> None:
    create_business_settings()
    working_hour = create_working_hours()
    service = create_service(duration_minutes=60)

    block_starts_at = datetime.combine(
        working_hour.date,
        time(hour=11),
        tzinfo=UTC,
    )
    block_ends_at = block_starts_at + timedelta(hours=1)

    create_calendar_block(
        starts_at=block_starts_at.isoformat(),
        ends_at=block_ends_at.isoformat(),
    )

    appointment_starts_at = block_starts_at - timedelta(minutes=30)

    _, token = user_with_login

    response = client.post(
        "/appointments/",
        json={
            "service_id": service.id,
            "starts_at": appointment_starts_at.isoformat(),
            "description": "Diseño francés con detalles dorados",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == "Horario bloqueado por el administrador"


def test_should_allow_appointment_ending_when_calendar_block_starts(
    client: TestClient,
    create_business_settings: Callable[..., BusinessSettingsRead],
    create_working_hours: Callable[..., WorkingHourRead],
    create_calendar_block: Callable[..., CalendarBlockRead],
    create_service: Callable[..., ServiceRead],
    user_with_login: tuple[UserRead, str],
) -> None:
    create_business_settings()
    working_hour = create_working_hours()
    service = create_service(
        duration_minutes=60,
        buffer_before_minutes=0,
        buffer_after_minutes=0,
    )

    block_starts_at = datetime.combine(
        working_hour.date,
        time(hour=11),
        tzinfo=UTC,
    )

    create_calendar_block(
        starts_at=block_starts_at.isoformat(),
        ends_at=(block_starts_at + timedelta(hours=1)).isoformat(),
    )

    appointment_starts_at = block_starts_at - timedelta(
        minutes=service.duration_minutes
    )

    _, token = user_with_login

    response = client.post(
        "/appointments/",
        json={
            "service_id": service.id,
            "starts_at": appointment_starts_at.isoformat(),
            "description": "Diseño francés con detalles dorados",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_201_CREATED


def test_should_allow_appointment_starting_when_calendar_block_ends(
    client: TestClient,
    create_business_settings: Callable[..., BusinessSettingsRead],
    create_working_hours: Callable[..., WorkingHourRead],
    create_calendar_block: Callable[..., CalendarBlockRead],
    create_service: Callable[..., ServiceRead],
    user_with_login: tuple[UserRead, str],
) -> None:
    create_business_settings()
    working_hour = create_working_hours()
    service = create_service(
        buffer_before_minutes=0,
        buffer_after_minutes=0,
    )

    block_starts_at = datetime.combine(
        working_hour.date,
        time(hour=11),
        tzinfo=UTC,
    )
    block_ends_at = block_starts_at + timedelta(hours=1)

    create_calendar_block(
        starts_at=block_starts_at.isoformat(),
        ends_at=block_ends_at.isoformat(),
    )

    _, token = user_with_login

    response = client.post(
        "/appointments/",
        json={
            "service_id": service.id,
            "starts_at": block_ends_at.isoformat(),
            "description": "Diseño francés con detalles dorados",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_201_CREATED
