from collections.abc import Callable
from datetime import datetime, timedelta

from fastapi import status
from fastapi.testclient import TestClient

from app.business_settings.schemas import BusinessSettingsRead
from app.services.schemas import ServiceRead
from app.users.schemas import UserRead
from app.working_hours.schemas import WorkingHourRead


def test_should_fail_if_appointment_starts_before_working_hours(
    client: TestClient,
    create_business_settings: Callable[..., BusinessSettingsRead],
    create_working_hours: Callable[..., WorkingHourRead],
    create_service: Callable[..., ServiceRead],
    user_with_login: tuple[UserRead, str],
) -> None:
    create_business_settings()
    working_hour = create_working_hours()
    service = create_service()

    starts_at = datetime.combine(
        working_hour.date,
        working_hour.start_time,
    ) - timedelta(hours=1)

    _, token = user_with_login

    response = client.post(
        "/appointments/",
        json={
            "service_id": service.id,
            "starts_at": starts_at.isoformat(),
            "description": "Diseño francés con detalles dorados",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert (
        response.json()["detail"]
        == "La cita solicitada está fuera del horario disponible"
    )


def test_should_fail_if_appointment_ends_after_working_hours(
    client: TestClient,
    create_business_settings: Callable[..., BusinessSettingsRead],
    create_working_hours: Callable[..., WorkingHourRead],
    create_service: Callable[..., ServiceRead],
    user_with_login: tuple[UserRead, str],
) -> None:
    create_business_settings()
    working_hour = create_working_hours()
    service = create_service()

    starts_at = (
        datetime.combine(
            working_hour.date,
            working_hour.end_time,
        )
        - timedelta(minutes=service.duration_minutes)
        + timedelta(hours=1)
    )

    _, token = user_with_login

    response = client.post(
        "/appointments/",
        json={
            "service_id": service.id,
            "starts_at": starts_at.isoformat(),
            "description": "Diseño francés con detalles dorados",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert (
        response.json()["detail"]
        == "La cita solicitada está fuera del horario disponible"
    )
