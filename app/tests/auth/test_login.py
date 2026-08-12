from collections.abc import Callable

from fastapi import status
from fastapi.testclient import TestClient

from app.core.database import Session
from app.core.enums import StatusEnum
from app.core.security import decode_token
from app.users.models import User
from app.users.schemas import UserRead


def create_test_user(
    create_user: Callable[..., UserRead],
    **overrides: object,
) -> UserRead:
    data = {
        "email": "test@example.com",
        "password": "Password123",
        "password2": "Password123",
        **overrides,
    }

    return create_user(**data)


def test_login_success(
    client: TestClient, create_user: Callable[..., UserRead]
) -> None:
    user = create_test_user(create_user)

    response = client.post(
        "/auth/login",
        data={
            "username": "test@example.com",
            "password": "Password123",
        },
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert data["token_type"] == "bearer"  # noqa: S105

    payload = decode_token(data["access_token"])

    assert payload["sub"] == str(user.id)
    assert payload["type"] == "access"


def test_login_wrong_password(
    client: TestClient,
    create_user: Callable[..., UserRead],
) -> None:
    create_test_user(create_user)

    response = client.post(
        "/auth/login",
        data={
            "username": "test@example.com",
            "password": "WrongPassword123",
        },
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Usuario o contraseña incorrectos"


def test_login_user_not_found(client: TestClient) -> None:
    response = client.post(
        "/auth/login",
        data={
            "username": "notfound@example.com",
            "password": "Password123",
        },
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Usuario o contraseña incorrectos"


def test_login_email_is_case_insensitive(
    client: TestClient,
    create_user: Callable[..., UserRead],
) -> None:
    create_test_user(create_user)

    response = client.post(
        "/auth/login",
        data={
            "username": "TEST@EXAMPLE.COM",
            "password": "Password123",
        },
    )

    assert response.status_code == status.HTTP_200_OK


def test_login_email_strips_whitespace(
    client: TestClient,
    create_user: Callable[..., UserRead],
) -> None:
    create_test_user(create_user)

    response = client.post(
        "/auth/login",
        data={
            "username": "  test@example.com  ",
            "password": "Password123",
        },
    )

    assert response.status_code == status.HTTP_200_OK


def test_login_missing_username(client: TestClient) -> None:
    response = client.post(
        "/auth/login",
        data={
            "password": "Password123",
        },
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_login_missing_password(client: TestClient) -> None:
    response = client.post(
        "/auth/login",
        data={
            "username": "test@example.com",
        },
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_login_empty_credentials(client: TestClient) -> None:
    response = client.post(
        "/auth/login",
        data={},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_login_inactive_user(
    client: TestClient,
    session: Session,
    create_user: Callable[..., UserRead],
) -> None:
    user_read = create_test_user(create_user)

    user = session.get(User, user_read.id)

    assert user is not None

    user.status = StatusEnum.INACTIVE
    session.commit()
    session.refresh(user)

    response = client.post(
        "/auth/login",
        data={
            "username": "test@example.com",
            "password": "Password123",
        },
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
