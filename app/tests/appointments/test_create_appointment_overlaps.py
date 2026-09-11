from collections.abc import Callable
from datetime import datetime, timedelta

from fastapi import status
from fastapi.testclient import TestClient

from app.appointments.schemas import AppointmentRead
from app.business_settings.schemas import BusinessSettingsRead
from app.services.schemas import ServiceRead
from app.users.schemas import UserRead
from app.working_hours.schemas import WorkingHourRead


def test_should_fail_if_appointment_overlaps_existing_appointment(
    client: TestClient,
    create_business_settings: Callable[..., BusinessSettingsRead],
    create_working_hours: Callable[..., WorkingHourRead],
    create_service: Callable[..., ServiceRead],
    create_appointment: Callable[..., AppointmentRead],
    user_with_login: tuple[UserRead, str],
) -> None:
    create_business_settings()
    working_hour = create_working_hours()
    service = create_service()

    starts_at = datetime.combine(working_hour.date, working_hour.start_time)

    user, token = user_with_login

    create_appointment(user_id=user.id, service=service, starts_at=starts_at)

    response = client.post(
        "/appointments/",
        json={
            "service_id": service.id,
            "starts_at": starts_at.isoformat(),
            "description": "  Diseño francés con detalles dorados  ",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == "Horario ya ocupado"


def test_should_fail_if_appointment_partially_overlaps_existing_appointment_from_left(
    client: TestClient,
    create_business_settings: Callable[..., BusinessSettingsRead],
    create_working_hours: Callable[..., WorkingHourRead],
    create_service: Callable[..., ServiceRead],
    create_appointment: Callable[..., AppointmentRead],
    user_with_login: tuple[UserRead, str],
) -> None:
    create_business_settings()
    working_hour = create_working_hours()
    service = create_service(duration_minutes=60)

    existing_starts_at = datetime.combine(
        working_hour.date,
        working_hour.start_time,
    ) + timedelta(hours=1)

    user, token = user_with_login

    create_appointment(
        user_id=user.id,
        service=service,
        starts_at=existing_starts_at,
    )

    new_starts_at = existing_starts_at - timedelta(minutes=30)

    response = client.post(
        "/appointments/",
        json={
            "service_id": service.id,
            "starts_at": new_starts_at.isoformat(),
            "description": "Diseño francés con detalles dorados",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == "Horario ya ocupado"


def test_should_fail_if_appointment_partially_overlaps_existing_appointment_from_right(
    client: TestClient,
    create_business_settings: Callable[..., BusinessSettingsRead],
    create_working_hours: Callable[..., WorkingHourRead],
    create_service: Callable[..., ServiceRead],
    create_appointment: Callable[..., AppointmentRead],
    user_with_login: tuple[UserRead, str],
) -> None:
    create_business_settings()
    working_hour = create_working_hours()
    service = create_service(duration_minutes=60)

    existing_starts_at = datetime.combine(
        working_hour.date,
        working_hour.start_time,
    ) + timedelta(hours=1)

    user, token = user_with_login

    create_appointment(
        user_id=user.id,
        service=service,
        starts_at=existing_starts_at,
    )

    new_starts_at = existing_starts_at + timedelta(minutes=30)

    response = client.post(
        "/appointments/",
        json={
            "service_id": service.id,
            "starts_at": new_starts_at.isoformat(),
            "description": "Diseño francés con detalles dorados",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == "Horario ya ocupado"


def test_should_fail_if_appointment_is_inside_existing_appointment(
    client: TestClient,
    create_business_settings: Callable[..., BusinessSettingsRead],
    create_working_hours: Callable[..., WorkingHourRead],
    create_service: Callable[..., ServiceRead],
    create_appointment: Callable[..., AppointmentRead],
    user_with_login: tuple[UserRead, str],
) -> None:
    create_business_settings()
    working_hour = create_working_hours()

    existing_service = create_service(
        name="Servicio largo",
        duration_minutes=120,
    )

    new_service = create_service(
        name="Servicio corto",
        duration_minutes=30,
    )

    existing_starts_at = datetime.combine(
        working_hour.date,
        working_hour.start_time,
    ) + timedelta(hours=1)

    user, token = user_with_login

    create_appointment(
        user_id=user.id,
        service=existing_service,
        starts_at=existing_starts_at,
    )

    new_starts_at = existing_starts_at + timedelta(minutes=30)

    response = client.post(
        "/appointments/",
        json={
            "service_id": new_service.id,
            "starts_at": new_starts_at.isoformat(),
            "description": "Diseño francés con detalles dorados",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == "Horario ya ocupado"


def test_should_fail_if_appointment_contains_existing_appointment(
    client: TestClient,
    create_business_settings: Callable[..., BusinessSettingsRead],
    create_working_hours: Callable[..., WorkingHourRead],
    create_service: Callable[..., ServiceRead],
    create_appointment: Callable[..., AppointmentRead],
    user_with_login: tuple[UserRead, str],
) -> None:
    create_business_settings()
    working_hour = create_working_hours()

    existing_service = create_service(
        name="Servicio largo",
        duration_minutes=120,
    )

    new_service = create_service(
        name="Servicio corto",
        duration_minutes=30,
    )

    existing_starts_at = datetime.combine(
        working_hour.date,
        working_hour.start_time,
    ) + timedelta(hours=2)

    user, token = user_with_login

    create_appointment(
        user_id=user.id,
        service=existing_service,
        starts_at=existing_starts_at,
    )

    new_starts_at = existing_starts_at - timedelta(minutes=30)

    response = client.post(
        "/appointments/",
        json={
            "service_id": new_service.id,
            "starts_at": new_starts_at.isoformat(),
            "description": "Diseño francés con detalles dorados",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == "Horario ya ocupado"


def test_should_allow_appointment_ending_when_existing_appointment_starts(
    client: TestClient,
    create_business_settings: Callable[..., BusinessSettingsRead],
    create_working_hours: Callable[..., WorkingHourRead],
    create_service: Callable[..., ServiceRead],
    create_appointment: Callable[..., AppointmentRead],
    user_with_login: tuple[UserRead, str],
) -> None:
    create_business_settings()
    working_hour = create_working_hours()
    service = create_service(
        duration_minutes=60,
        buffer_before_minutes=0,
        buffer_after_minutes=0,
    )

    existing_starts_at = datetime.combine(
        working_hour.date,
        working_hour.start_time,
    ) + timedelta(hours=2)

    user, token = user_with_login

    create_appointment(
        user_id=user.id,
        service=service,
        starts_at=existing_starts_at,
    )

    new_starts_at = existing_starts_at - timedelta(minutes=service.duration_minutes)

    response = client.post(
        "/appointments/",
        json={
            "service_id": service.id,
            "starts_at": new_starts_at.isoformat(),
            "description": "Diseño francés con detalles dorados",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_201_CREATED


def test_should_allow_appointment_starting_when_existing_appointment_ends(
    client: TestClient,
    create_business_settings: Callable[..., BusinessSettingsRead],
    create_working_hours: Callable[..., WorkingHourRead],
    create_service: Callable[..., ServiceRead],
    create_appointment: Callable[..., AppointmentRead],
    user_with_login: tuple[UserRead, str],
) -> None:
    create_business_settings()
    working_hour = create_working_hours()
    service = create_service(
        duration_minutes=60,
        buffer_before_minutes=0,
        buffer_after_minutes=0,
    )

    existing_starts_at = datetime.combine(
        working_hour.date,
        working_hour.start_time,
    ) + timedelta(hours=1)

    user, token = user_with_login

    existing_appointment = create_appointment(
        user_id=user.id,
        service=service,
        starts_at=existing_starts_at,
    )

    response = client.post(
        "/appointments/",
        json={
            "service_id": service.id,
            "starts_at": existing_appointment.ends_at.isoformat(),
            "description": "Diseño francés con detalles dorados",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_201_CREATED
