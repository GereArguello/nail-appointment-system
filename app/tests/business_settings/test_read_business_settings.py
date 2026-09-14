from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.business_settings.models import BusinessSettings
from app.users.schemas import UserRead


def test_should_create_default_business_settings(
    session: Session, client: TestClient, admin_with_login: tuple[UserRead, str]
) -> None:
    _, token = admin_with_login

    response = client.get(
        "business-settings", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == status.HTTP_200_OK

    business_settings = session.get(BusinessSettings, 1)

    assert business_settings is not None
    assert business_settings.id == 1
    assert business_settings.appointment_end_tolerance_minutes == 10
    assert business_settings.appointment_start_tolerance_minutes == 10
    assert business_settings.deposit_payment_expiration_hours == 24


def test_should_read_existing_business_settings(
    session: Session,
    client: TestClient,
    admin_with_login: tuple[UserRead, str],
) -> None:
    _, token = admin_with_login

    business_settings = BusinessSettings(
        id=1,
        appointment_end_tolerance_minutes=15,
    )

    session.add(business_settings)
    session.commit()

    response = client.get(
        "/business-settings/",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert data["id"] == 1
    assert data["appointment_end_tolerance_minutes"] == 15


def test_should_not_create_duplicate_business_settings(
    session: Session,
    client: TestClient,
    admin_with_login: tuple[UserRead, str],
) -> None:
    _, token = admin_with_login

    response = client.get(
        "/business-settings/",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_200_OK

    response = client.get(
        "/business-settings/",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_200_OK

    business_settings = session.exec(select(BusinessSettings)).all()

    assert len(business_settings) == 1
    assert business_settings[0].id == 1


def test_should_reject_non_admin_user(
    client: TestClient,
    user_with_login: tuple[UserRead, str],
) -> None:
    _, token = user_with_login

    response = client.get(
        "/business-settings/",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_should_reject_unauthenticated_user(
    client: TestClient,
) -> None:
    response = client.get("/business-settings/")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
