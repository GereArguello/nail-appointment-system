from collections.abc import Callable

from fastapi import status
from fastapi.testclient import TestClient

from app.services.schemas import ServiceRead
from app.users.schemas import UserRead


def test_should_read_service_successfully(
    client: TestClient,
    create_service: Callable[..., ServiceRead],
) -> None:
    service = create_service()

    response = client.get(f"/services/{service.id}")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert data["id"] == service.id
    assert data["name"] == service.name
    assert data["description"] == service.description
    assert data["duration_minutes"] == service.duration_minutes
    assert data["price"] == service.price
    assert data["status"] == service.status.value


def test_should_return_404_if_service_does_not_exist(
    client: TestClient,
) -> None:
    response = client.get("/services/999999")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Servicio no encontrado"


def test_should_return_404_if_inactive_service_is_requested_without_authentication(
    client: TestClient,
    inactive_service: ServiceRead,
) -> None:
    response = client.get(f"/services/{inactive_service.id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_should_return_inactive_service_to_admin(
    client: TestClient,
    admin_with_login: tuple[UserRead, str],
    inactive_service: ServiceRead,
) -> None:
    _, token = admin_with_login

    response = client.get(
        f"/services/{inactive_service.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert data["id"] == inactive_service.id
    assert data["status"] == inactive_service.status.value


def test_should_return_404_if_regular_user_requests_inactive_service(
    client: TestClient,
    user_with_login: tuple[UserRead, str],
    inactive_service: ServiceRead,
) -> None:
    _, token = user_with_login

    response = client.get(
        f"/services/{inactive_service.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
