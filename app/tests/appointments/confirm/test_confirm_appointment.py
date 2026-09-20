from collections.abc import Callable
from datetime import UTC, datetime

from fastapi import status
from fastapi.testclient import TestClient

from app.appointments.schemas import AppointmentRead
from app.core.enums import AppointmentStatusEnum
from app.services.schemas import ServiceRead
from app.users.schemas import UserRead


def test_should_confirm_appointment(
    client: TestClient,
    appointment: AppointmentRead,
    admin_with_login: tuple[UserRead, str],
) -> None:
    _, token = admin_with_login

    appointment_id = appointment.id

    response = client.patch(
        f"/appointments/{appointment_id}/confirm",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_200_OK

    assert response.json()["status"] == AppointmentStatusEnum.CONFIRMED


def test_should_fail_to_confirm_appointment_if_status_is_not_pending_confirmation(
    client: TestClient,
    create_appointment: Callable[..., AppointmentRead],
    create_service: Callable[..., ServiceRead],
    admin_with_login: tuple[UserRead, str],
    user_with_login: tuple[UserRead, str],
) -> None:
    user, _ = user_with_login
    _, token = admin_with_login

    service = create_service()

    appointment = create_appointment(
        user_id=user.id,
        service=service,
        starts_at=datetime.now(UTC),
        status=AppointmentStatusEnum.PENDING_PAYMENT,
    )

    response = client.patch(
        f"/appointments/{appointment.id}/confirm",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert (
        response.json()["detail"]
        == "La cita no puede ser confirmada en su estado actual"
    )


def test_should_fail_to_confirm_appointment_if_not_found(
    client: TestClient,
    admin_with_login: tuple[UserRead, str],
) -> None:
    _, token = admin_with_login

    response = client.patch(
        "/appointments/999/confirm",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_should_fail_to_confirm_appointment_if_user_is_not_admin(
    client: TestClient,
    create_appointment: Callable[..., AppointmentRead],
    create_service: Callable[..., ServiceRead],
    user_with_login: tuple[UserRead, str],
) -> None:
    user, token = user_with_login

    service = create_service()

    appointment = create_appointment(
        user_id=user.id,
        service=service,
        starts_at=datetime.now(UTC),
    )

    response = client.patch(
        f"/appointments/{appointment.id}/confirm",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
