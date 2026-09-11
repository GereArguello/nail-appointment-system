from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from fastapi import status
from fastapi.testclient import TestClient

from app.business_settings.schemas import BusinessSettingsRead
from app.core.enums import AppointmentStatusEnum
from app.services.schemas import ServiceRead
from app.users.schemas import UserRead
from app.utils import as_utc
from app.working_hours.schemas import WorkingHourRead


def test_should_create_appointment(
    client: TestClient,
    create_business_settings: Callable[..., BusinessSettingsRead],
    create_working_hours: Callable[..., WorkingHourRead],
    create_service: Callable[..., ServiceRead],
    user_with_login: tuple[UserRead, str],
) -> None:
    create_business_settings()
    working_hour = create_working_hours()
    service = create_service()

    starts_at = datetime.combine(working_hour.date, working_hour.start_time)

    user, token = user_with_login

    response = client.post(
        "/appointments/",
        json={
            "service_id": service.id,
            "starts_at": starts_at.isoformat(),
            "description": "  Diseño francés con detalles dorados  ",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()

    assert data["user_id"] == user.id
    assert data["service_id"] == service.id

    assert data["starts_at"] == starts_at.isoformat()
    assert (
        data["ends_at"]
        == (starts_at + timedelta(minutes=service.duration_minutes)).isoformat()
    )

    assert data["status"] == AppointmentStatusEnum.PENDING_CONFIRMATION.value

    assert data["agreed_price"] == service.price
    assert data["agreed_deposit"] == service.deposit_amount
    assert data["payment_expires_at"] is None

    assert data["description"] == "Diseño francés con detalles dorados"

    created_at = as_utc(datetime.fromisoformat(data["created_at"]))
    updated_at = as_utc(datetime.fromisoformat(data["updated_at"]))

    assert created_at <= datetime.now(UTC)
    assert updated_at <= datetime.now(UTC)


def test_should_fail_if_service_does_not_exist(
    client: TestClient,
    create_business_settings: Callable[..., BusinessSettingsRead],
    create_working_hours: Callable[..., WorkingHourRead],
    user_with_login: tuple[UserRead, str],
) -> None:
    create_business_settings()
    working_hour = create_working_hours()

    starts_at = datetime.combine(
        working_hour.date,
        working_hour.start_time,
    )

    _, token = user_with_login

    response = client.post(
        "/appointments/",
        json={
            "service_id": 999999,
            "starts_at": starts_at.isoformat(),
            "description": "Diseño francés",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Servicio no encontrado"


def test_should_fail_without_authentication(
    client: TestClient,
    create_business_settings: Callable[..., BusinessSettingsRead],
    create_working_hours: Callable[..., WorkingHourRead],
    create_service: Callable[..., ServiceRead],
) -> None:
    create_business_settings()
    working_hour = create_working_hours()
    service = create_service()

    starts_at = datetime.combine(
        working_hour.date,
        working_hour.start_time,
    )

    response = client.post(
        "/appointments/",
        json={
            "service_id": service.id,
            "starts_at": starts_at.isoformat(),
            "description": "Diseño francés",
        },
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_should_fail_if_starts_at_is_in_the_past(
    client: TestClient,
    create_business_settings: Callable[..., BusinessSettingsRead],
    create_service: Callable[..., ServiceRead],
    user_with_login: tuple[UserRead, str],
) -> None:
    create_business_settings()
    service = create_service()

    starts_at = datetime.now(UTC) - timedelta(days=1)

    _, token = user_with_login

    response = client.post(
        "/appointments/",
        json={
            "service_id": service.id,
            "starts_at": starts_at.isoformat(),
            "description": "Diseño francés",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert (
        response.json()["detail"][0]["msg"]
        == "Value error, La fecha de la cita no puede estar en el pasado"
    )


def test_should_allow_appointment_without_description(
    client: TestClient,
    create_business_settings: Callable[..., BusinessSettingsRead],
    create_working_hours: Callable[..., WorkingHourRead],
    create_service: Callable[..., ServiceRead],
    user_with_login: tuple[UserRead, str],
) -> None:
    create_business_settings()
    working_hour = create_working_hours()

    service = create_service(
        buffer_before_minutes=0,
        buffer_after_minutes=0,
    )

    starts_at = datetime.combine(
        working_hour.date,
        working_hour.start_time,
    )

    _, token = user_with_login

    response = client.post(
        "/appointments/",
        json={
            "service_id": service.id,
            "starts_at": starts_at.isoformat(),
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()

    assert data["description"] is None
