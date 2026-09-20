from collections.abc import Callable
from datetime import datetime, timedelta

from fastapi import Response, status

from app.services.schemas import ServiceRead
from app.users.schemas import UserRead
from app.working_hours.schemas import WorkingHourRead


def test_should_fail_if_appointment_starts_before_working_hours(
    appointment_creation_setup: tuple[ServiceRead, WorkingHourRead, datetime],
    user_with_login: tuple[UserRead, str],
    post_appointment: Callable[..., Response],
) -> None:
    service, working_hour, _ = appointment_creation_setup

    starts_at = datetime.combine(
        working_hour.date,
        working_hour.start_time,
    ) - timedelta(hours=1)

    _, token = user_with_login

    response = post_appointment(
        service_id=service.id,
        starts_at=starts_at,
        token=token,
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert (
        response.json()["detail"]
        == "La cita solicitada está fuera del horario disponible"
    )


def test_should_fail_if_appointment_ends_after_working_hours(
    appointment_creation_setup: tuple[ServiceRead, WorkingHourRead, datetime],
    user_with_login: tuple[UserRead, str],
    post_appointment: Callable[..., Response],
) -> None:
    service, working_hour, _ = appointment_creation_setup

    latest_valid_start = datetime.combine(
        working_hour.date,
        working_hour.end_time,
    ) - timedelta(minutes=service.duration_minutes)

    starts_at = latest_valid_start + timedelta(minutes=1)

    _, token = user_with_login

    response = post_appointment(
        service_id=service.id,
        starts_at=starts_at,
        token=token,
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert (
        response.json()["detail"]
        == "La cita solicitada está fuera del horario disponible"
    )
