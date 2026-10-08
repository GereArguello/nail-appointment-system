from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from fastapi import Response, status
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.business_settings.schemas import BusinessSettingsRead
from app.core.datetime import as_utc, localize_business_datetime
from app.core.enums import AppointmentStatusEnum, StatusEnum
from app.services.models import Service
from app.services.schemas import ServiceRead
from app.users.schemas import UserRead
from app.working_hours.schemas import WorkingHourRead


def test_should_create_appointment(
    appointment_creation_setup: tuple[
        BusinessSettingsRead, ServiceRead, WorkingHourRead, datetime
    ],
    user_with_login: tuple[UserRead, str],
    post_appointment: Callable[..., Response],
) -> None:
    business_settings, service, _, starts_at = appointment_creation_setup

    user, token = user_with_login

    response = post_appointment(
        service_id=service.id,
        starts_at=starts_at,
        token=token,
    )

    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()

    assert data["user_id"] == user.id
    assert data["service_id"] == service.id

    response_starts_at = as_utc(datetime.fromisoformat(data["starts_at"]))
    response_ends_at = as_utc(datetime.fromisoformat(data["ends_at"]))

    expected_starts_at = localize_business_datetime(
        starts_at,
        business_settings.timezone,
    ).astimezone(UTC)

    expected_ends_at = expected_starts_at + timedelta(minutes=service.duration_minutes)

    assert response_starts_at == expected_starts_at
    assert response_ends_at == expected_ends_at

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
    user_with_login: tuple[UserRead, str],
    post_appointment: Callable[..., Response],
) -> None:
    _, token = user_with_login

    starts_at = datetime.now() + timedelta(days=1)

    response = post_appointment(
        service_id=99999,
        starts_at=starts_at,
        token=token,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Servicio no encontrado"


def test_should_fail_if_service_is_inactive(
    session: Session,
    appointment_creation_setup: tuple[
        BusinessSettingsRead, ServiceRead, WorkingHourRead, datetime
    ],
    user_with_login: tuple[UserRead, str],
    post_appointment: Callable[..., Response],
) -> None:
    _, service, _, starts_at = appointment_creation_setup

    db_service = session.get(Service, service.id)

    assert db_service is not None

    db_service.status = StatusEnum.INACTIVE
    session.commit()

    _, token = user_with_login

    response = post_appointment(
        service_id=service.id,
        starts_at=starts_at,
        token=token,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Servicio no encontrado"


def test_should_fail_without_authentication(
    client: TestClient,
    appointment_creation_setup: tuple[
        BusinessSettingsRead, ServiceRead, WorkingHourRead, datetime
    ],
) -> None:
    _, service, _, starts_at = appointment_creation_setup

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
    create_business_settings: Callable[..., BusinessSettingsRead],
    create_service: Callable[..., ServiceRead],
    user_with_login: tuple[UserRead, str],
    post_appointment: Callable[..., Response],
) -> None:
    create_business_settings()
    service = create_service()

    starts_at = datetime.now() - timedelta(days=1)

    _, token = user_with_login

    response = post_appointment(
        service_id=service.id,
        starts_at=starts_at,
        token=token,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert (
        response.json()["detail"][0]["msg"]
        == "Value error, La fecha de la cita no puede estar en el pasado"
    )


def test_should_allow_appointment_without_description(
    appointment_creation_setup: tuple[
        BusinessSettingsRead, ServiceRead, WorkingHourRead, datetime
    ],
    user_with_login: tuple[UserRead, str],
    post_appointment: Callable[..., Response],
) -> None:
    _, service, _, starts_at = appointment_creation_setup

    _, token = user_with_login

    response = post_appointment(
        service_id=service.id, starts_at=starts_at, token=token, description=None
    )

    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()

    assert data["description"] is None
