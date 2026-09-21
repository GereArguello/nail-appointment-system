from collections.abc import Callable

from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.business_settings.models import BusinessSettings
from app.business_settings.schemas import BusinessSettingsRead
from app.users.schemas import UserRead


def test_should_update_all_business_settings_fields(
    client: TestClient,
    session: Session,
    create_business_settings: Callable[..., BusinessSettingsRead],
    admin_with_login: tuple[UserRead, str],
) -> None:
    _, token = admin_with_login

    create_business_settings()

    response = client.patch(
        "/business-settings/",
        json={
            "appointment_start_tolerance_minutes": 15,
            "appointment_end_tolerance_minutes": 20,
            "appointment_cancellation_limit_hours": 12,
            "slot_interval_minutes": 30,
            "deposit_payment_expiration_hours": 48,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_200_OK

    settings = session.get(BusinessSettings, 1)

    assert settings is not None
    assert settings.appointment_start_tolerance_minutes == 15
    assert settings.appointment_end_tolerance_minutes == 20
    assert settings.appointment_cancellation_limit_hours == 12
    assert settings.slot_interval_minutes == 30
    assert settings.deposit_payment_expiration_hours == 48


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
