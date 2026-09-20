from datetime import timedelta

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.appointments.models import Appointment
from app.appointments.schemas import AppointmentRead
from app.core.enums import AppointmentStatusEnum
from app.users.schemas import UserRead
from app.utils import utc_now


def test_should_complete_confirmed_appointment(
    client: TestClient,
    session: Session,
    appointment: AppointmentRead,
    admin_with_login: tuple[UserRead, str],
) -> None:
    _, token = admin_with_login

    db_appointment = session.get(Appointment, appointment.id)

    assert db_appointment is not None

    db_appointment.status = AppointmentStatusEnum.CONFIRMED
    db_appointment.ends_at = utc_now() - timedelta(minutes=30)

    session.commit()

    response = client.patch(
        f"/appointments/{appointment.id}/complete",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == AppointmentStatusEnum.COMPLETED


@pytest.mark.parametrize(
    "appointment_status",
    [
        AppointmentStatusEnum.PENDING_PAYMENT,
        AppointmentStatusEnum.PENDING_CONFIRMATION,
        AppointmentStatusEnum.COMPLETED,
        AppointmentStatusEnum.CANCELLED_BY_CLIENT,
        AppointmentStatusEnum.CANCELLED_BY_ADMIN,
        AppointmentStatusEnum.NO_SHOW,
    ],
)
def test_should_not_complete_appointment_when_status_is_not_confirmed(
    client: TestClient,
    session: Session,
    appointment: AppointmentRead,
    admin_with_login: tuple[UserRead, str],
    appointment_status: AppointmentStatusEnum,
) -> None:
    _, token = admin_with_login

    db_appointment = session.get(Appointment, appointment.id)

    assert db_appointment is not None

    db_appointment.status = appointment_status
    db_appointment.ends_at = utc_now() - timedelta(minutes=30)

    session.commit()

    response = client.patch(
        f"/appointments/{appointment.id}/complete",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert (
        response.json()["detail"]
        == "La cita no puede ser completada en su estado actual"
    )


def test_should_not_complete_appointment_before_end_time(
    client: TestClient,
    session: Session,
    appointment: AppointmentRead,
    admin_with_login: tuple[UserRead, str],
) -> None:
    _, token = admin_with_login

    db_appointment = session.get(Appointment, appointment.id)

    assert db_appointment is not None

    db_appointment.status = AppointmentStatusEnum.CONFIRMED
    db_appointment.ends_at = utc_now() + timedelta(hours=1)

    session.commit()

    response = client.patch(
        f"/appointments/{appointment.id}/complete",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert (
        response.json()["detail"]
        == "La cita no puede completarse antes de su finalización"
    )


def test_should_return_404_when_appointment_does_not_exist(
    client: TestClient,
    admin_with_login: tuple[UserRead, str],
) -> None:
    _, token = admin_with_login

    response = client.patch(
        "/appointments/999999/complete",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Cita no encontrada"
