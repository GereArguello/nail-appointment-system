from collections.abc import Callable
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.business_settings.schemas import BusinessSettingsRead
from app.tests.utils import get_local_date
from app.users.schemas import UserRead


def test_should_create_working_hours_as_admin(
    client: TestClient,
    admin_with_login: tuple[UserRead, str],
    create_business_settings: Callable[..., BusinessSettingsRead],
) -> None:
    business_settings = create_business_settings()
    _, token = admin_with_login

    date = get_local_date(
        days_offset=5,
        timezone=business_settings.timezone,
    )

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
    create_business_settings: Callable[..., BusinessSettingsRead],
) -> None:
    business_settings = create_business_settings()
    _, token = admin_with_login

    date = get_local_date(
        days_offset=5,
        timezone=business_settings.timezone,
    )

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

    date = get_local_date(
        days_offset=5,
    )

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
    create_business_settings: Callable[..., BusinessSettingsRead],
) -> None:
    business_settings = create_business_settings()
    _, token = admin_with_login

    date = get_local_date(
        days_offset=-1,
        timezone=business_settings.timezone,
    )

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
    client: TestClient,
    admin_with_login: tuple[UserRead, str],
    create_business_settings: Callable[..., BusinessSettingsRead],
) -> None:
    business_settings = create_business_settings()
    _, token = admin_with_login

    date = get_local_date(
        days_offset=5,
        timezone=business_settings.timezone,
    )

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
    date = get_local_date(
        days_offset=5,
    )

    response = client.post(
        "/working-hours/",
        json={
            "date": date,
            "start_time": "09:00:00",
            "end_time": "18:00:00",
        },
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_should_use_business_timezone_when_validating_working_hour_date(
    client: TestClient,
    admin_with_login: tuple[UserRead, str],
    create_business_settings: Callable[..., BusinessSettingsRead],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifica que la validación utilice la fecha local del negocio.

    Simula un instante en el que UTC ya es 16 de octubre, pero en
    Buenos Aires todavía es 15 de octubre.

    Comprueba que se permita crear un horario para el día 15,
    evitando que se rechace incorrectamente como una fecha pasada.
    """
    create_business_settings()

    _, token = admin_with_login

    fixed_utc = datetime(
        2026,
        10,
        16,
        2,
        0,
        tzinfo=UTC,
    )

    monkeypatch.setattr(
        "app.working_hours.routes.get_now_in_timezone",
        lambda timezone: fixed_utc.astimezone(ZoneInfo(timezone.value)),
    )

    response = client.post(
        "/working-hours/",
        json={
            "date": "2026-10-15",
            "start_time": "09:00:00",
            "end_time": "18:00:00",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["date"] == "2026-10-15"
