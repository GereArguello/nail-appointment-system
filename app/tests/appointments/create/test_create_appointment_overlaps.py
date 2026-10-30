from collections.abc import Callable
from datetime import datetime, timedelta

import pytest
from fastapi import Response, status
from sqlmodel import Session

from app.appointments.models import Appointment
from app.appointments.schemas import AppointmentRead
from app.business_settings.schemas import BusinessSettingsRead
from app.core.enums import AppointmentStatusEnum
from app.services.schemas import ServiceRead
from app.tests.helpers import as_local_naive
from app.users.schemas import UserRead
from app.working_hours.schemas import WorkingHourRead


@pytest.mark.parametrize(
    "appointment_status",
    [
        AppointmentStatusEnum.CANCELLED_BY_CLIENT,
        AppointmentStatusEnum.CANCELLED_BY_ADMIN,
        AppointmentStatusEnum.NO_SHOW,
    ],
)
def test_should_allow_overlapping_appointment_when_existing_status_does_not_block(
    session: Session,
    appointment_status: AppointmentStatusEnum,
    appointment_overlap_setup: tuple[
        BusinessSettingsRead, ServiceRead, AppointmentRead, str
    ],
    post_appointment: Callable[..., Response],
) -> None:
    business_settings, service, appointment, token = appointment_overlap_setup

    db_appointment = session.get(Appointment, appointment.id)

    assert db_appointment is not None

    db_appointment.status = appointment_status

    session.commit()
    session.refresh(db_appointment)

    starts_at = as_local_naive(appointment.starts_at, business_settings.timezone)

    response = post_appointment(
        service_id=service.id,
        starts_at=starts_at,
        token=token,
    )

    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.parametrize(
    "appointment_status",
    [
        AppointmentStatusEnum.CONFIRMED,
        AppointmentStatusEnum.PENDING_CONFIRMATION,
        AppointmentStatusEnum.PENDING_PAYMENT,
    ],
)
def test_should_fail_if_existing_appointment_status_blocks(
    session: Session,
    appointment_status: AppointmentStatusEnum,
    appointment_overlap_setup: tuple[
        BusinessSettingsRead, ServiceRead, AppointmentRead, str
    ],
    post_appointment: Callable[..., Response],
) -> None:
    business_settings, service, appointment, token = appointment_overlap_setup

    db_appointment = session.get(Appointment, appointment.id)

    assert db_appointment is not None

    db_appointment.status = appointment_status

    session.commit()
    session.refresh(db_appointment)

    starts_at = as_local_naive(appointment.starts_at, business_settings.timezone)

    response = post_appointment(
        service_id=service.id,
        starts_at=starts_at,
        token=token,
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == "Horario ya ocupado"


def test_should_fail_if_appointment_partially_overlaps_existing_appointment_from_left(
    appointment_overlap_setup: tuple[
        BusinessSettingsRead, ServiceRead, AppointmentRead, str
    ],
    post_appointment: Callable[..., Response],
) -> None:
    business_settings, service, appointment, token = appointment_overlap_setup

    starts_at = as_local_naive(appointment.starts_at, business_settings.timezone)

    new_starts_at = starts_at - timedelta(minutes=30)

    response = post_appointment(
        service_id=service.id,
        starts_at=new_starts_at,
        token=token,
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == "Horario ya ocupado"


def test_should_fail_if_appointment_partially_overlaps_existing_appointment_from_right(
    appointment_overlap_setup: tuple[
        BusinessSettingsRead, ServiceRead, AppointmentRead, str
    ],
    post_appointment: Callable[..., Response],
) -> None:
    business_settings, service, appointment, token = appointment_overlap_setup

    starts_at = as_local_naive(appointment.starts_at, business_settings.timezone)

    new_starts_at = starts_at + timedelta(minutes=30)

    response = post_appointment(
        service_id=service.id,
        starts_at=new_starts_at,
        token=token,
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == "Horario ya ocupado"


def test_should_fail_if_appointment_is_inside_existing_appointment(
    appointment_overlap_context: tuple[
        BusinessSettingsRead, WorkingHourRead, UserRead, str
    ],
    create_service: Callable[..., ServiceRead],
    create_appointment: Callable[..., AppointmentRead],
    post_appointment: Callable[..., Response],
) -> None:
    _, working_hour, user, token = appointment_overlap_context

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
    appointment_overlap_context: tuple[
        BusinessSettingsRead, WorkingHourRead, UserRead, str
    ],
    create_service: Callable[..., ServiceRead],
    create_appointment: Callable[..., AppointmentRead],
    post_appointment: Callable[..., Response],
) -> None:
    _, working_hour, user, token = appointment_overlap_context

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

    create_appointment(
        user_id=user.id,
        service=service,
        starts_at=existing_starts_at,
    )

    new_starts_at = existing_starts_at + timedelta(minutes=service.duration_minutes)

    response = post_appointment(
        service_id=service.id,
        starts_at=new_starts_at,
        token=token,
    )

    assert response.status_code == status.HTTP_201_CREATED


def test_should_fail_if_appointment_overlaps_existing_buffer_before(
    appointment_overlap_context: tuple[
        BusinessSettingsRead, WorkingHourRead, UserRead, str
    ],
    create_service: Callable[..., ServiceRead],
    create_appointment: Callable[..., AppointmentRead],
    post_appointment: Callable[..., Response],
) -> None:
    _, working_hour, user, token = appointment_overlap_context

    service = create_service(
        name="Servicio con buffer previo",
        duration_minutes=60,
        buffer_before_minutes=15,
    )

    existing_starts_at = datetime.combine(
        working_hour.date,
        working_hour.start_time,
    ) + timedelta(hours=2)

    create_appointment(
        user_id=user.id,
        service=service,
        starts_at=existing_starts_at,
    )

    new_starts_at = existing_starts_at - timedelta(minutes=45)

    response = post_appointment(
        service_id=service.id,
        starts_at=new_starts_at,
        token=token,
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == "Horario ya ocupado"


def test_should_fail_if_appointment_overlaps_existing_buffer_after(
    appointment_overlap_context: tuple[
        BusinessSettingsRead, WorkingHourRead, UserRead, str
    ],
    create_service: Callable[..., ServiceRead],
    create_appointment: Callable[..., AppointmentRead],
    post_appointment: Callable[..., Response],
) -> None:
    business_settings, working_hour, user, token = appointment_overlap_context

    service = create_service(
        name="Servicio con buffer posterior",
        duration_minutes=60,
        buffer_after_minutes=15,
    )

    existing_starts_at = datetime.combine(
        working_hour.date,
        working_hour.start_time,
    ) + timedelta(hours=1)

    existing_appointment = create_appointment(
        user_id=user.id,
        service=service,
        starts_at=existing_starts_at,
    )

    new_starts_at = as_local_naive(
        existing_appointment.ends_at, business_settings.timezone
    ) + timedelta(minutes=5)

    response = post_appointment(
        service_id=service.id,
        starts_at=new_starts_at,
        token=token,
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == "Horario ya ocupado"
