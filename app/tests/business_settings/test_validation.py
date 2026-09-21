from collections.abc import Callable

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.business_settings.schemas import BusinessSettingsRead
from app.users.schemas import UserRead


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("appointment_start_tolerance_minutes", -1),
        ("appointment_end_tolerance_minutes", -1),
        ("appointment_cancellation_limit_hours", -1),
        ("deposit_payment_expiration_hours", 0),
        ("deposit_payment_expiration_hours", 169),
    ],
)
def test_should_reject_invalid_business_settings_values(
    client: TestClient,
    create_business_settings: Callable[..., BusinessSettingsRead],
    admin_with_login: tuple[UserRead, str],
    field: str,
    value: int,
) -> None:
    _, token = admin_with_login

    create_business_settings()

    response = client.patch(
        "/business-settings/",
        json={field: value},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.parametrize("value", [5, 65])
def test_should_reject_slot_interval_out_of_range(
    client: TestClient,
    create_business_settings: Callable[..., BusinessSettingsRead],
    admin_with_login: tuple[UserRead, str],
    value: int,
) -> None:
    _, token = admin_with_login

    create_business_settings()

    response = client.patch(
        "/business-settings/",
        json={"slot_interval_minutes": value},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_should_reject_slot_interval_not_multiple_of_5(
    client: TestClient,
    create_business_settings: Callable[..., BusinessSettingsRead],
    admin_with_login: tuple[UserRead, str],
) -> None:
    _, token = admin_with_login

    create_business_settings()

    response = client.patch(
        "/business-settings/",
        json={"slot_interval_minutes": 29},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.parametrize("value", [10, 60])
def test_should_allow_slot_interval_boundary_values(
    client: TestClient,
    create_business_settings: Callable[..., BusinessSettingsRead],
    admin_with_login: tuple[UserRead, str],
    value: int,
) -> None:
    _, token = admin_with_login

    create_business_settings()

    response = client.patch(
        "/business-settings/",
        json={"slot_interval_minutes": value},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_200_OK
