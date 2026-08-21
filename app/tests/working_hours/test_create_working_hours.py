from datetime import timedelta

from fastapi import status
from fastapi.testclient import TestClient

from app.users.schemas import UserRead
from app.utils import utc_now


def test_should_create_working_hours_as_admin(
    client: TestClient, admin_with_login: tuple[UserRead, str]
) -> None:
    _, token = admin_with_login

    date = (utc_now() + timedelta(days=5)).date().isoformat()

    response = client.post(
        "/working-hours/",
        json={"date": date, "start_time": "09:00:00", "end_time": "18:00:00"},
        headers={"Authorization": f"bearer {token}"},
    )

    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()

    assert data["date"] == date
    assert data["start_time"] == "09:00:00"
    assert data["end_time"] == "18:00:00"


def test_should_reject_duplicate_working_hours_date(
    client: TestClient,
    admin_with_login: tuple[UserRead, str],
) -> None:
    _, token = admin_with_login

    date = (utc_now() + timedelta(days=5)).date().isoformat()

    payload = {
        "date": date,
        "start_time": "09:00:00",
        "end_time": "18:00:00",
    }

    first_response = client.post(
        "/working-hours/",
        json=payload,
        headers={"Authorization": f"bearer {token}"},
    )

    assert first_response.status_code == status.HTTP_201_CREATED

    second_response = client.post(
        "/working-hours/",
        json=payload,
        headers={"Authorization": f"bearer {token}"},
    )

    assert second_response.status_code == status.HTTP_409_CONFLICT
    assert second_response.json()["detail"] == "Ya existe un registro con este día"


def test_should_reject_non_admin_user(
    client: TestClient,
    user_with_login: tuple[UserRead, str],
) -> None:
    _, token = user_with_login

    date = (utc_now() + timedelta(days=5)).date().isoformat()

    response = client.post(
        "/working-hours/",
        json={
            "date": date,
            "start_time": "09:00:00",
            "end_time": "18:00:00",
        },
        headers={"Authorization": f"bearer {token}"},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_should_reject_past_date(
    client: TestClient,
    admin_with_login: tuple[UserRead, str],
) -> None:
    _, token = admin_with_login

    date = (utc_now() - timedelta(days=1)).date().isoformat()

    response = client.post(
        "/working-hours/",
        json={
            "date": date,
            "start_time": "09:00:00",
            "end_time": "18:00:00",
        },
        headers={"Authorization": f"bearer {token}"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_should_reject_end_time_before_start_time(
    client: TestClient, admin_with_login: tuple[UserRead, str]
) -> None:
    _, token = admin_with_login

    date = (utc_now() + timedelta(days=5)).date().isoformat()

    response = client.post(
        "/working-hours/",
        json={"date": date, "start_time": "10:00:00", "end_time": "09:00:00"},
        headers={"Authorization": f"bearer {token}"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    assert (
        "La hora de finalización debe ser posterior a la hora de inicio"
        in response.json()["detail"][0]["msg"]
    )


def test_should_reject_unauthenticated_user(
    client: TestClient,
) -> None:
    date = (utc_now() + timedelta(days=5)).date().isoformat()

    response = client.post(
        "/working-hours/",
        json={
            "date": date,
            "start_time": "09:00:00",
            "end_time": "18:00:00",
        },
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
