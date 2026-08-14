from fastapi import status
from fastapi.testclient import TestClient

from app.users.schemas import UserRead


def test_get_current_user(
    client: TestClient,
    user_with_login: tuple[UserRead, str],
) -> None:
    user, access_token = user_with_login

    response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == user.model_dump(mode="json")


def test_get_current_user_without_token(client: TestClient) -> None:
    response = client.get("/users/me")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_current_user_with_invalid_token(client: TestClient) -> None:
    response = client.get(
        "/users/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
