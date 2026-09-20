from datetime import timedelta

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.appointments.models import Appointment
from app.appointments.schemas import AppointmentRead
from app.business_settings.models import BusinessSettings
from app.core.enums import AppointmentStatusEnum
from app.users.schemas import UserRead
from app.utils import utc_now


@pytest.mark.parametrize(
    "appointment_status",
    [
        AppointmentStatusEnum.PENDING_PAYMENT,
        AppointmentStatusEnum.PENDING_CONFIRMATION,
        AppointmentStatusEnum.CONFIRMED,
    ],
)
def test_should_cancel_appointment_when_status_is_cancellable(
    client: TestClient,
    session: Session,
    appointment: AppointmentRead,
    user_with_login: tuple[UserRead, str],
    appointment_status: AppointmentStatusEnum,
) -> None:
    _, token = user_with_login

    db_appointment = session.get(Appointment, appointment.id)

    assert db_appointment is not None

    db_appointment.status = appointment_status

    if appointment_status == AppointmentStatusEnum.CONFIRMED:
        db_appointment.starts_at = utc_now() + timedelta(days=2)

    session.commit()

    response = client.patch(
        f"/appointments/{appointment.id}/cancel",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == AppointmentStatusEnum.CANCELLED_BY_CLIENT


def test_should_cancel_appointment_when_requested_by_admin(
    client: TestClient,
    appointment: AppointmentRead,
    admin_with_login: tuple[UserRead, str],
) -> None:
    _, token = admin_with_login

    appointment_id = appointment.id

    response = client.patch(
        f"/appointments/{appointment_id}/cancel",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == AppointmentStatusEnum.CANCELLED_BY_ADMIN


def test_should_allow_admin_to_cancel_after_cancellation_deadline(
    client: TestClient,
    session: Session,
    appointment: AppointmentRead,
    admin_with_login: tuple[UserRead, str],
) -> None:
    _, token = admin_with_login

    business_settings = session.get(BusinessSettings, 1)

    assert business_settings is not None

    business_settings.appointment_cancellation_limit_hours = 24

    db_appointment = session.get(Appointment, appointment.id)

    assert db_appointment is not None

    db_appointment.status = AppointmentStatusEnum.CONFIRMED
    db_appointment.starts_at = utc_now() + timedelta(hours=12)

    session.commit()

    response = client.patch(
        f"/appointments/{appointment.id}/cancel",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == AppointmentStatusEnum.CANCELLED_BY_ADMIN


def test_should_not_cancel_appointment_when_requested_by_other_user(
    client: TestClient,
    appointment: AppointmentRead,
    another_user_with_login: tuple[UserRead, str],
) -> None:
    _, token = another_user_with_login

    appointment_id = appointment.id

    response = client.patch(
        f"/appointments/{appointment_id}/cancel",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND

    assert response.json()["detail"] == "Cita no encontrada"


@pytest.mark.parametrize(
    "appointment_status",
    [
        AppointmentStatusEnum.COMPLETED,
        AppointmentStatusEnum.CANCELLED_BY_CLIENT,
        AppointmentStatusEnum.CANCELLED_BY_ADMIN,
    ],
)
def test_should_not_cancel_appointment_when_status_is_not_cancellable(
    client: TestClient,
    session: Session,
    appointment: AppointmentRead,
    user_with_login: tuple[UserRead, str],
    appointment_status: AppointmentStatusEnum,
) -> None:
    _, token = user_with_login

    db_appointment = session.get(Appointment, appointment.id)

    assert db_appointment is not None

    db_appointment.status = appointment_status
    session.commit()

    response = client.patch(
        f"/appointments/{appointment.id}/cancel",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert (
        response.json()["detail"]
        == "La cita no puede ser cancelada en su estado actual"
    )


def test_should_not_cancel_appointment_after_cancellation_deadline(
    client: TestClient,
    session: Session,
    appointment: AppointmentRead,
    user_with_login: tuple[UserRead, str],
) -> None:
    _, token = user_with_login

    business_settings = session.get(BusinessSettings, 1)

    assert business_settings is not None

    business_settings.appointment_cancellation_limit_hours = 24

    db_appointment = session.get(Appointment, appointment.id)

    assert db_appointment is not None

    db_appointment.status = AppointmentStatusEnum.CONFIRMED
    db_appointment.starts_at = utc_now() + timedelta(hours=12)

    session.commit()

    response = client.patch(
        f"/appointments/{appointment.id}/cancel",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_409_CONFLICT


def test_should_return_404_when_appointment_does_not_exist(
    client: TestClient,
    user_with_login: tuple[UserRead, str],
) -> None:
    _, token = user_with_login

    response = client.patch(
        "/appointments/999999/cancel",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Cita no encontrada"
