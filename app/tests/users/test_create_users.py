from collections.abc import Callable
from datetime import date, timedelta

from fastapi import status
from fastapi.testclient import TestClient

from app.tests.factories import create_data
from app.users.schemas import UserRead


def test_should_fail_if_passwords_dont_match(client: TestClient) -> None:
    data = create_data(
        password2="A87654321",
    )

    response = client.post("/users/", json=data)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert "Las contraseñas no coinciden" in response.json()["detail"][0]["msg"]


def test_should_fail_if_email_is_invalid(client: TestClient) -> None:
    data = create_data(email="no-es-un-email")

    response = client.post("/users/", json=data)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_should_fail_if_password_has_no_uppercase(client: TestClient) -> None:
    data = create_data(
        password="abc123456",
        password2="abc123456",
    )

    response = client.post("/users/", json=data)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert (
        "La contraseña debe contener al menos una mayúscula"
        in response.json()["detail"][0]["msg"]
    )


def test_should_fail_if_password_has_no_digit(client: TestClient) -> None:
    data = create_data(
        password="Abcdefghi",
        password2="Abcdefghi",
    )

    response = client.post("/users/", json=data)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert (
        "La contraseña debe contener al menos un número"
        in response.json()["detail"][0]["msg"]
    )


def test_should_fail_if_birth_date_is_in_the_future(client: TestClient) -> None:
    data = create_data(birth_date=(date.today() + timedelta(days=1)).isoformat())

    response = client.post("/users/", json=data)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert (
        "La fecha de nacimiento no puede ser futura"
        in response.json()["detail"][0]["msg"]
    )


def test_should_create_user_successfully(client: TestClient) -> None:
    data = create_data()

    response = client.post("/users/", json=data)

    assert response.status_code == status.HTTP_201_CREATED


def test_should_fail_if_email_already_exists(
    client: TestClient,
    create_user: Callable[[], UserRead],
) -> None:
    create_user()

    data = create_data()

    response = client.post("/users/", json=data)

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == "El email ya está registrado"
