from collections.abc import Callable
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import status
from fastapi.testclient import TestClient

from app.appointments.schemas import AppointmentRead
from app.business_settings.schemas import BusinessSettingsRead
from app.services.schemas import ServiceRead
from app.users.schemas import UserRead


def test_should_return_all_appointments_if_user_is_admin(
    client: TestClient,
    admin_with_login: tuple[UserRead, str],
    appointments: list[AppointmentRead],
) -> None:
    _, token = admin_with_login

    response = client.get("/appointments", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    returned_ids = {appointment["id"] for appointment in data}
    expected_ids = {appointment.id for appointment in appointments}

    assert returned_ids == expected_ids


def test_should_return_only_user_appointments(
    client: TestClient,
    appointments: list[AppointmentRead],
    create_appointment: Callable[..., AppointmentRead],
    create_service: Callable[..., ServiceRead],
    user_with_login: tuple[UserRead, str],
    another_user: UserRead,
) -> None:
    user, token = user_with_login

    service = create_service(name="otro servicio")

    create_appointment(
        user_id=another_user.id,
        service=service,
        starts_at=datetime.now() + timedelta(days=10),
    )

    response = client.get(
        "/appointments",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert len(data) == len(appointments)
    assert all(appointment["user_id"] == user.id for appointment in data)


def test_should_return_empty_list_if_user_has_no_appointments(
    client: TestClient,
    user_with_login: tuple[UserRead, str],
    create_business_settings: Callable[..., BusinessSettingsRead],
) -> None:
    create_business_settings()
    _, token = user_with_login

    response = client.get(
        "/appointments",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_should_filter_appointments_by_from_date(
    client: TestClient,
    appointments: list[AppointmentRead],
    admin_with_login: tuple[UserRead, str],
    create_business_settings: Callable[..., BusinessSettingsRead],
) -> None:
    business_settings = create_business_settings()
    _, token = admin_with_login

    from_date = (
        appointments[2]
        .starts_at.astimezone(ZoneInfo(business_settings.timezone))
        .date()
    )

    response = client.get(
        "/appointments",
        params={"from_date": from_date.isoformat()},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert all(
        datetime.fromisoformat(appointment["starts_at"])
        .astimezone(ZoneInfo(business_settings.timezone))
        .date()
        >= from_date
        for appointment in data
    )


def test_should_filter_appointments_by_to_date(
    client: TestClient,
    appointments: list[AppointmentRead],
    admin_with_login: tuple[UserRead, str],
    create_business_settings: Callable[..., BusinessSettingsRead],
) -> None:
    business_settings = create_business_settings()
    _, token = admin_with_login

    to_date = (
        appointments[2]
        .starts_at.astimezone(ZoneInfo(business_settings.timezone))
        .date()
    )

    response = client.get(
        "/appointments",
        params={"to_date": to_date.isoformat()},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert all(
        datetime.fromisoformat(appointment["starts_at"])
        .astimezone(ZoneInfo(business_settings.timezone))
        .date()
        <= to_date
        for appointment in data
    )


def test_should_filter_appointments_by_date_range(
    client: TestClient,
    appointments: list[AppointmentRead],
    admin_with_login: tuple[UserRead, str],
    create_business_settings: Callable[..., BusinessSettingsRead],
) -> None:
    business_settings = create_business_settings()
    _, token = admin_with_login

    from_date = (
        appointments[1]
        .starts_at.astimezone(ZoneInfo(business_settings.timezone))
        .date()
    )
    to_date = (
        appointments[3]
        .starts_at.astimezone(ZoneInfo(business_settings.timezone))
        .date()
    )

    response = client.get(
        "/appointments",
        params={
            "from_date": from_date.isoformat(),
            "to_date": to_date.isoformat(),
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert all(
        from_date
        <= datetime.fromisoformat(appointment["starts_at"])
        .astimezone(ZoneInfo(business_settings.timezone))
        .date()
        <= to_date
        for appointment in data
    )

    returned_ids = {appointment["id"] for appointment in data}
    expected_ids = {
        appointment.id
        for appointment in appointments
        if from_date
        <= appointment.starts_at.astimezone(ZoneInfo(business_settings.timezone)).date()
        <= to_date
    }

    assert returned_ids == expected_ids


def test_should_fail_if_to_date_is_before_from_date(
    client: TestClient,
    admin_with_login: tuple[UserRead, str],
    create_business_settings: Callable[..., BusinessSettingsRead],
) -> None:
    business_settings = create_business_settings()
    _, token = admin_with_login

    from_date = datetime.now(ZoneInfo(business_settings.timezone)).date()

    to_date = from_date - timedelta(days=1)

    response = client.get(
        "/appointments",
        params={
            "from_date": from_date.isoformat(),
            "to_date": to_date.isoformat(),
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == (
        "La fecha final no puede ser anterior a la inicial"
    )


def test_should_fail_to_list_appointments_if_user_is_not_authenticated(
    client: TestClient,
) -> None:
    response = client.get("/appointments")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
