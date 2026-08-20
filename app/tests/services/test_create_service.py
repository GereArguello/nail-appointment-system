from collections.abc import Callable

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.services.schemas import ServiceRead
from app.tests.factories import create_service_data
from app.users.schemas import UserRead


def test_should_create_service(
    client: TestClient, admin_with_login: tuple[UserRead, str]
) -> None:
    _, token = admin_with_login
    data = create_service_data()

    response = client.post(
        "/services/", json=data, headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == status.HTTP_201_CREATED

    response_data = response.json()

    assert response_data["name"] == data["name"]
    assert response_data["description"] == data["description"]
    assert response_data["duration_minutes"] == data["duration_minutes"]
    assert response_data["price"] == data["price"]
    assert response_data["id"] is not None
    assert response_data["status"] == "active"
    assert response_data["created_at"] is not None
    assert response_data["updated_at"] is not None


def test_should_return_403_if_user_is_not_admin(
    client: TestClient, user_with_login: tuple[UserRead, str]
) -> None:
    _, token = user_with_login
    data = create_service_data()

    response = client.post(
        "/services", json=data, headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_should_return_401_if_no_token_is_provided(client: TestClient) -> None:
    data = create_service_data()

    response = client.post("/services", json=data)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_should_return_409_if_service_name_already_exists(
    client: TestClient,
    admin_with_login: tuple[UserRead, str],
    create_service: Callable[..., ServiceRead],
) -> None:
    _, token = admin_with_login

    service = create_service()

    data = create_service_data(name=service.name)

    response = client.post(
        "/services/",
        json=data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == "Ya existe un servicio con ese nombre"


def test_should_return_422_if_deposit_is_greater_than_price(
    client: TestClient,
    admin_with_login: tuple[UserRead, str],
) -> None:
    _, token = admin_with_login

    data = create_service_data(
        price=10000,
        deposit_amount=15000,
    )

    response = client.post(
        "/services/",
        json=data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("duration_minutes", 0),
        ("price", 0),
    ],
)
def test_should_return_422_if_positive_field_is_not_positive(
    client: TestClient,
    admin_with_login: tuple[UserRead, str],
    field: str,
    value: int,
) -> None:
    _, token = admin_with_login

    data = create_service_data(**{field: value})

    response = client.post(
        "/services/",
        json=data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("buffer_before_minutes", -1),
        ("buffer_after_minutes", -1),
        ("deposit_amount", -1),
    ],
)
def test_should_return_422_if_non_negative_field_is_negative(
    client: TestClient,
    admin_with_login: tuple[UserRead, str],
    field: str,
    value: int,
) -> None:
    _, token = admin_with_login
    data = create_service_data(**{field: value})

    response = client.post(
        "/services/",
        json=data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_should_normalize_service_name(
    client: TestClient,
    admin_with_login: tuple[UserRead, str],
) -> None:
    _, token = admin_with_login

    data = create_service_data(name="   Manicura clásica   ")

    response = client.post(
        "/services/",
        json=data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["name"] == "Manicura clásica"


def test_should_normalize_service_description(
    client: TestClient,
    admin_with_login: tuple[UserRead, str],
) -> None:
    _, token = admin_with_login

    data = create_service_data(
        description="   Servicio de manicura clásica   ",
    )

    response = client.post(
        "/services/",
        json=data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["description"] == "Servicio de manicura clásica"


def test_should_convert_empty_description_to_none(
    client: TestClient,
    admin_with_login: tuple[UserRead, str],
) -> None:
    _, token = admin_with_login

    data = create_service_data(description="   ")

    response = client.post(
        "/services/",
        json=data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["description"] is None


def test_should_return_422_if_name_is_only_whitespace(
    client: TestClient,
    admin_with_login: tuple[UserRead, str],
) -> None:
    _, token = admin_with_login

    data = create_service_data(name="   ")

    response = client.post(
        "/services/",
        json=data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
