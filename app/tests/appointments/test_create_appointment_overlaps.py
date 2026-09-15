from collections.abc import Callable
from datetime import datetime, timedelta

from fastapi import Response, status

from app.appointments.schemas import AppointmentRead
from app.services.schemas import ServiceRead
from app.users.schemas import UserRead
from app.working_hours.schemas import WorkingHourRead


def test_should_fail_if_appointment_overlaps_existing_appointment(
    appointment_overlap_setup: tuple[ServiceRead, AppointmentRead, str],
    post_appointment: Callable[..., Response],
) -> None:
    service, appointment, token = appointment_overlap_setup

    response = post_appointment(
        service_id=service.id,
        starts_at=appointment.starts_at,
        token=token,
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == "Horario ya ocupado"


def test_should_fail_if_appointment_partially_overlaps_existing_appointment_from_left(
    appointment_overlap_setup: tuple[ServiceRead, AppointmentRead, str],
    post_appointment: Callable[..., Response],
) -> None:
    service, appointment, token = appointment_overlap_setup

    new_starts_at = appointment.starts_at - timedelta(minutes=30)

    response = post_appointment(
        service_id=service.id,
        starts_at=new_starts_at,
        token=token,
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == "Horario ya ocupado"


def test_should_fail_if_appointment_partially_overlaps_existing_appointment_from_right(
    appointment_overlap_setup: tuple[ServiceRead, AppointmentRead, str],
    post_appointment: Callable[..., Response],
) -> None:
    service, appointment, token = appointment_overlap_setup

    new_starts_at = appointment.starts_at + timedelta(minutes=30)

    response = post_appointment(
        service_id=service.id,
        starts_at=new_starts_at,
        token=token,
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == "Horario ya ocupado"


def test_should_fail_if_appointment_is_inside_existing_appointment(
    appointment_overlap_context: tuple[WorkingHourRead, UserRead, str],
    create_service: Callable[..., ServiceRead],
    create_appointment: Callable[..., AppointmentRead],
    post_appointment: Callable[..., Response],
) -> None:
    working_hour, user, token = appointment_overlap_context

    existing_service = create_service(
        name="Servicio largo",
        duration_minutes=120,
    )

    new_service = create_service(
        name="Servicio corto",
        duration_minutes=30,
    )

    existing_starts_at = datetime.combine(
        working_hour.date,
        working_hour.start_time,
    ) + timedelta(hours=1)

    create_appointment(
        user_id=user.id,
        service=existing_service,
        starts_at=existing_starts_at,
    )

    new_starts_at = existing_starts_at + timedelta(minutes=30)

    response = post_appointment(
        service_id=new_service.id,
        starts_at=new_starts_at,
        token=token,
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == "Horario ya ocupado"


def test_should_fail_if_appointment_contains_existing_appointment(
    appointment_overlap_context: tuple[WorkingHourRead, UserRead, str],
    create_service: Callable[..., ServiceRead],
    create_appointment: Callable[..., AppointmentRead],
    post_appointment: Callable[..., Response],
) -> None:
    working_hour, user, token = appointment_overlap_context

    existing_service = create_service(
        name="Servicio corto",
        duration_minutes=30,
    )

    new_service = create_service(
        name="Servicio largo",
        duration_minutes=120,
    )

    existing_starts_at = datetime.combine(
        working_hour.date,
        working_hour.start_time,
    ) + timedelta(hours=2)

    create_appointment(
        user_id=user.id,
        service=existing_service,
        starts_at=existing_starts_at,
    )

    new_starts_at = existing_starts_at - timedelta(minutes=30)

    response = post_appointment(
        service_id=new_service.id,
        starts_at=new_starts_at,
        token=token,
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == "Horario ya ocupado"


def test_should_allow_appointment_ending_when_existing_appointment_starts(
    create_appointment: Callable[..., AppointmentRead],
    post_appointment: Callable[..., Response],
    adjacent_appointment_setup: Callable[
        ..., tuple[ServiceRead, datetime, UserRead, str]
    ],
) -> None:
    service, existing_starts_at, user, token = adjacent_appointment_setup(
        start_offset_hours=2
    )

    create_appointment(
        user_id=user.id,
        service=service,
        starts_at=existing_starts_at,
    )

    new_starts_at = existing_starts_at - timedelta(minutes=service.duration_minutes)

    response = post_appointment(
        service_id=service.id,
        starts_at=new_starts_at,
        token=token,
    )

    assert response.status_code == status.HTTP_201_CREATED


def test_should_allow_appointment_starting_when_existing_appointment_ends(
    create_appointment: Callable[..., AppointmentRead],
    post_appointment: Callable[..., Response],
    adjacent_appointment_setup: Callable[
        ..., tuple[ServiceRead, datetime, UserRead, str]
    ],
) -> None:
    service, existing_starts_at, user, token = adjacent_appointment_setup(
        start_offset_hours=1
    )

    existing_appointment = create_appointment(
        user_id=user.id,
        service=service,
        starts_at=existing_starts_at,
    )

    response = post_appointment(
        service_id=service.id,
        starts_at=existing_appointment.ends_at,
        token=token,
    )

    assert response.status_code == status.HTTP_201_CREATED
