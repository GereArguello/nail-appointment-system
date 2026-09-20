from collections.abc import Callable
from datetime import datetime, timedelta

from fastapi import Response, status

from app.calendar_blocks.schemas import CalendarBlockRead
from app.services.schemas import ServiceRead
from app.users.schemas import UserRead
from app.working_hours.schemas import WorkingHourRead


def test_should_fail_if_appointment_overlaps_calendar_block(
    create_calendar_block: Callable[..., CalendarBlockRead],
    user_with_login: tuple[UserRead, str],
    appointment_creation_setup: tuple[ServiceRead, WorkingHourRead, datetime],
    post_appointment: Callable[..., Response],
) -> None:
    service, _, starts_at = appointment_creation_setup

    create_calendar_block(
        starts_at=starts_at.isoformat(),
        ends_at=(starts_at + timedelta(hours=1)).isoformat(),
    )

    _, token = user_with_login

    response = post_appointment(
        service_id=service.id,
        starts_at=starts_at,
        token=token,
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == "Horario bloqueado por el administrador"


def test_should_fail_if_appointment_partially_overlaps_calendar_block(
    appointment_creation_setup: tuple[ServiceRead, WorkingHourRead, datetime],
    calendar_block_setup: tuple[datetime, datetime],
    user_with_login: tuple[UserRead, str],
    post_appointment: Callable[..., Response],
) -> None:
    service, _, _ = appointment_creation_setup
    block_starts_at, _ = calendar_block_setup

    appointment_starts_at = block_starts_at - timedelta(minutes=30)

    _, token = user_with_login

    response = post_appointment(
        service_id=service.id,
        starts_at=appointment_starts_at,
        token=token,
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == "Horario bloqueado por el administrador"


def test_should_allow_appointment_ending_when_calendar_block_starts(
    calendar_block_setup: tuple[datetime, datetime],
    create_service: Callable[..., ServiceRead],
    user_with_login: tuple[UserRead, str],
    post_appointment: Callable[..., Response],
) -> None:
    block_starts_at, _ = calendar_block_setup

    service = create_service(
        name="Servicio sin buffers",
        buffer_before_minutes=0,
        buffer_after_minutes=0,
    )

    appointment_starts_at = block_starts_at - timedelta(
        minutes=service.duration_minutes
    )

    _, token = user_with_login

    response = post_appointment(
        service_id=service.id,
        starts_at=appointment_starts_at,
        token=token,
    )

    assert response.status_code == status.HTTP_201_CREATED


def test_should_allow_appointment_starting_when_calendar_block_ends(
    calendar_block_setup: tuple[datetime, datetime],
    create_service: Callable[..., ServiceRead],
    user_with_login: tuple[UserRead, str],
    post_appointment: Callable[..., Response],
) -> None:
    _, block_ends_at = calendar_block_setup

    service = create_service(
        name="Servicio sin buffers",
        buffer_before_minutes=0,
        buffer_after_minutes=0,
    )

    _, token = user_with_login

    response = post_appointment(
        service_id=service.id,
        starts_at=block_ends_at,
        token=token,
    )

    assert response.status_code == status.HTTP_201_CREATED
