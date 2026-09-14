from collections.abc import Callable
from datetime import datetime

from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.business_settings.models import BusinessSettings
from app.business_settings.schemas import BusinessSettingsRead
from app.users.schemas import UserRead


def test_should_update_business_settings(
    client: TestClient,
    session: Session,
    create_business_settings: Callable[..., BusinessSettingsRead],
    admin_with_login: tuple[UserRead, str],
) -> None:
    _, token = admin_with_login

    business_settings = create_business_settings()

    response = client.patch(
        "/business-settings/",
        json={"appointment_end_tolerance_minutes": 15},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    previous_updated_at = business_settings.updated_at
    updated_at = datetime.fromisoformat(data["updated_at"])

    assert data["id"] == 1
    assert data["appointment_end_tolerance_minutes"] == 15
    assert updated_at > previous_updated_at

    business_settings = session.get(BusinessSettings, 1)

    assert business_settings is not None
    assert business_settings.appointment_end_tolerance_minutes == 15


def test_should_create_and_update_business_settings_if_not_exists(
    client: TestClient,
    session: Session,
    admin_with_login: tuple[UserRead, str],
) -> None:
    _, token = admin_with_login

    response = client.patch(
        "/business-settings/",
        json={"appointment_end_tolerance_minutes": 15},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_200_OK

    business_settings = session.get(BusinessSettings, 1)

    assert business_settings is not None
    assert business_settings.appointment_end_tolerance_minutes == 15


def test_should_reject_negative_appointment_end_tolerance_minutes(
    client: TestClient,
    create_business_settings: Callable[..., BusinessSettingsRead],
    admin_with_login: tuple[UserRead, str],
) -> None:
    _, token = admin_with_login

    create_business_settings()

    response = client.patch(
        "/business-settings/",
        json={"appointment_end_tolerance_minutes": -1},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_should_reject_non_admin_user_when_updating_business_settings(
    client: TestClient,
    create_business_settings: Callable[..., BusinessSettingsRead],
    user_with_login: tuple[UserRead, str],
) -> None:
    _, token = user_with_login

    create_business_settings()

    response = client.patch(
        "/business-settings/",
        json={"appointment_end_tolerance_minutes": 15},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_should_reject_unauthenticated_user_when_updating_business_settings(
    client: TestClient,
    create_business_settings: Callable[..., BusinessSettingsRead],
) -> None:
    create_business_settings()

    response = client.patch(
        "/business-settings/",
        json={"appointment_end_tolerance_minutes": 15},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_should_allow_empty_update_business_settings(
    client: TestClient,
    session: Session,
    create_business_settings: Callable[..., BusinessSettingsRead],
    admin_with_login: tuple[UserRead, str],
) -> None:
    _, token = admin_with_login

    create_business_settings(
        appointment_end_tolerance_minutes=10,
    )

    response = client.patch(
        "/business-settings/",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_200_OK

    business_settings = session.get(BusinessSettings, 1)

    assert business_settings is not None
    assert business_settings.appointment_end_tolerance_minutes == 10
