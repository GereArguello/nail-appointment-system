from collections.abc import Callable

from fastapi import status
from fastapi.testclient import TestClient

from app.appointments.schemas import AppointmentRead
from app.users.schemas import UserRead


def test_should_read_appointment_if_user_is_owner(
    client: TestClient,
    user_with_login: tuple[UserRead, str],
    appointment: AppointmentRead,
) -> None:

    _, token = user_with_login

    response = client.get(
        f"/appointments/{appointment.id}", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == status.HTTP_200_OK


def test_should_read_appointment_if_user_is_admin(
    client: TestClient,
    admin_with_login: tuple[UserRead, str],
    appointment: AppointmentRead,
) -> None:

    _, token = admin_with_login

    response = client.get(
        f"/appointments/{appointment.id}", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == status.HTTP_200_OK


def test_should_return_404_if_user_is_not_owner_or_admin(
    client: TestClient,
    create_user: Callable[..., UserRead],
    appointment: AppointmentRead,
) -> None:
    user = create_user(email="test2@example.com")

    login = client.post(
        "/auth/login",
        data={"username": user.email, "password": "A12345678"},
    )

    token = login.json()["access_token"]

    response = client.get(
        f"/appointments/{appointment.id}", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_should_return_404_if_appointment_not_exists(
    client: TestClient,
    user_with_login: tuple[UserRead, str],
) -> None:
    _, token = user_with_login

    response = client.get(
        "/appointments/999999",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Turno no encontrado"
