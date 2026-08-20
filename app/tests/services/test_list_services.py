from collections.abc import Callable

from fastapi import status
from fastapi.testclient import TestClient

from app.core.enums import StatusEnum
from app.services.schemas import ServiceRead
from app.users.schemas import UserRead


def test_should_return_active_services(
    client: TestClient,
    user_with_login: tuple[UserRead, str],
    create_service: Callable[..., ServiceRead],
) -> None:
    service = create_service()

    _, token = user_with_login

    response = client.get(
        "/services",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert isinstance(data, list)
    assert len(data) == 1

    assert data[0]["id"] == service.id
    assert data[0]["name"] == service.name
    assert data[0]["price"] == service.price
    assert data[0]["status"] == service.status.value


def test_should_not_return_inactive_services_to_regular_user(
    client: TestClient,
    user_with_login: tuple[UserRead, str],
    create_service: Callable[..., ServiceRead],
    inactive_service: ServiceRead,
) -> None:
    active_service = create_service(name="Servicio activo")

    _, token = user_with_login

    response = client.get(
        "/services/",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == active_service.id
    assert data[0]["status"] == StatusEnum.ACTIVE.value


def test_should_return_only_active_services_without_authentication(
    client: TestClient,
    create_service: Callable[..., ServiceRead],
    inactive_service: ServiceRead,
) -> None:
    active_service = create_service(name="Servicio activo")

    response = client.get("/services/")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == active_service.id
    assert data[0]["status"] == StatusEnum.ACTIVE.value


def test_should_return_active_and_inactive_services_to_admin(
    client: TestClient,
    admin_with_login: tuple[UserRead, str],
    create_service: Callable[..., ServiceRead],
    inactive_service: ServiceRead,
) -> None:
    active_service = create_service(name="Servicio activo")
    _, token = admin_with_login

    response = client.get(
        "/services/",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert len(data) == 2

    ids = {service["id"] for service in data}

    assert active_service.id in ids
    assert inactive_service.id in ids


def test_should_return_only_active_services_to_admin_when_filtering_by_active(
    client: TestClient,
    admin_with_login: tuple[UserRead, str],
    create_service: Callable[..., ServiceRead],
    inactive_service: ServiceRead,
) -> None:
    active_service = create_service(name="Servicio activo")

    _, token = admin_with_login

    response = client.get(
        "/services/?status=active",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == active_service.id
    assert data[0]["status"] == StatusEnum.ACTIVE.value


def test_should_return_only_inactive_services_to_admin_when_filtering_by_inactive(
    client: TestClient,
    admin_with_login: tuple[UserRead, str],
    create_service: Callable[..., ServiceRead],
    inactive_service: ServiceRead,
) -> None:
    create_service(name="Servicio activo")

    _, token = admin_with_login

    response = client.get(
        "/services/?status=inactive",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == inactive_service.id
    assert data[0]["status"] == StatusEnum.INACTIVE.value


def test_should_return_empty_list_if_no_services_exist(
    client: TestClient,
) -> None:
    response = client.get("/services/")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []
