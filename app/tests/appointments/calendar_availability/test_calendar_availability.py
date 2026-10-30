from collections.abc import Callable
from datetime import date, datetime, time, timedelta

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.appointments.helper import calculate_first_and_last_possible_start
from app.appointments.schemas import AppointmentRead
from app.business_settings.schemas import BusinessSettingsRead
from app.business_settings.service import get_business_now, get_business_settings_or_409
from app.calendar_blocks.schemas import CalendarBlockRead
from app.core.enums import AppointmentStatusEnum
from app.services.schemas import ServiceRead
from app.users.schemas import UserRead
from app.working_hours.models import WorkingHour
from app.working_hours.schemas import WorkingHourRead


def test_calendar_availability_with_working_hours(
    create_working_hours_list: Callable[[int], list[WorkingHourRead]],
    create_service: Callable[..., ServiceRead],
    client: TestClient,
) -> None:
    service = create_service()
    working_hours = create_working_hours_list(7)

    from_date = working_hours[0].date
    to_date = working_hours[-1].date

    response = client.get(
        "/appointments/availability/calendar",
        params={
            "from_date": from_date.isoformat(),
            "to_date": to_date.isoformat(),
            "service_id": service.id,
        },
    )

    assert response.status_code == status.HTTP_200_OK

    expected_response = [
        {
            "date": wh.date.isoformat(),
            "available": True,
        }
        for wh in working_hours
    ]

    assert response.json() == expected_response


def test_calendar_availability_without_working_hour(
    create_working_hours_list: Callable[[int], list[WorkingHourRead]],
    create_service: Callable[..., ServiceRead],
    client: TestClient,
) -> None:
    service = create_service()
    working_hours = create_working_hours_list(6)

    from_date = working_hours[0].date
    to_date = working_hours[-1].date + timedelta(days=1)

    response = client.get(
        "/appointments/availability/calendar",
        params={
            "from_date": from_date.isoformat(),
            "to_date": to_date.isoformat(),
            "service_id": service.id,
        },
    )

    assert response.status_code == status.HTTP_200_OK

    expected_response = [
        {
            "date": wh.date.isoformat(),
            "available": True,
        }
        for wh in working_hours
    ]

    expected_response.append(
        {
            "date": to_date.isoformat(),
            "available": False,
        }
    )

    assert response.json() == expected_response


def test_calendar_availability_fully_booked_day(
    create_working_hours_list: Callable[[int], list[WorkingHourRead]],
    create_service: Callable[..., ServiceRead],
    create_appointment: Callable[..., AppointmentRead],
    user_with_login: tuple[UserRead, str],
    session: Session,
    client: TestClient,
) -> None:
    service = create_service(
        duration_minutes=60,
        buffer_before_minutes=0,
        buffer_after_minutes=0,
    )
    working_hours = create_working_hours_list(3)
    user, _ = user_with_login

    business_settings = get_business_settings_or_409(session)

    middle_day = working_hours[1]

    first, last = calculate_first_and_last_possible_start(
        middle_day,
        service,
        business_settings,
    )

    step = timedelta(minutes=60)

    current = first

    while current <= last:
        create_appointment(
            user_id=user.id,
            service=service,
            starts_at=current.replace(tzinfo=None),
        )

        current += step

    response = client.get(
        "/appointments/availability/calendar",
        params={
            "from_date": working_hours[0].date.isoformat(),
            "to_date": working_hours[-1].date.isoformat(),
            "service_id": service.id,
        },
    )

    assert response.status_code == status.HTTP_200_OK

    expected_response = [
        {"date": working_hours[0].date.isoformat(), "available": True},
        {"date": working_hours[1].date.isoformat(), "available": False},
        {"date": working_hours[2].date.isoformat(), "available": True},
    ]

    assert response.json() == expected_response


def test_calendar_availability_partially_booked_day(
    create_working_hours_list: Callable[[int], list[WorkingHourRead]],
    create_service: Callable[..., ServiceRead],
    create_appointment: Callable[..., AppointmentRead],
    user_with_login: tuple[UserRead, str],
    session: Session,
    client: TestClient,
) -> None:
    service = create_service(
        duration_minutes=60,
        buffer_before_minutes=0,
        buffer_after_minutes=0,
    )
    working_hours = create_working_hours_list(3)
    user, _ = user_with_login

    business_settings = get_business_settings_or_409(session)

    middle_day = working_hours[1]

    first, _ = calculate_first_and_last_possible_start(
        middle_day,
        service,
        business_settings,
    )

    for i in range(4):
        starts_at = first + timedelta(minutes=60 * i)

        create_appointment(
            user_id=user.id,
            service=service,
            starts_at=starts_at.replace(tzinfo=None),
        )

    response = client.get(
        "/appointments/availability/calendar",
        params={
            "from_date": working_hours[0].date.isoformat(),
            "to_date": working_hours[-1].date.isoformat(),
            "service_id": service.id,
        },
    )

    assert response.status_code == status.HTTP_200_OK

    expected_response = [
        {"date": working_hours[0].date.isoformat(), "available": True},
        {"date": working_hours[1].date.isoformat(), "available": True},
        {"date": working_hours[2].date.isoformat(), "available": True},
    ]

    assert response.json() == expected_response


def test_calendar_availability_fully_blocked_day(
    create_working_hours_list: Callable[[int], list[WorkingHourRead]],
    create_service: Callable[..., ServiceRead],
    create_calendar_block: Callable[..., CalendarBlockRead],
    client: TestClient,
) -> None:
    service = create_service()
    working_hours = create_working_hours_list(3)

    middle_day = working_hours[1]

    starts_at = datetime.combine(
        middle_day.date,
        middle_day.start_time,
    )

    ends_at = datetime.combine(
        middle_day.date,
        middle_day.end_time,
    )

    create_calendar_block(
        starts_at=starts_at.isoformat(),
        ends_at=ends_at.isoformat(),
    )

    response = client.get(
        "/appointments/availability/calendar",
        params={
            "from_date": working_hours[0].date.isoformat(),
            "to_date": working_hours[-1].date.isoformat(),
            "service_id": service.id,
        },
    )

    assert response.status_code == status.HTTP_200_OK

    expected_response = [
        {"date": working_hours[0].date.isoformat(), "available": True},
        {"date": working_hours[1].date.isoformat(), "available": False},
        {"date": working_hours[2].date.isoformat(), "available": True},
    ]

    assert response.json() == expected_response


def test_calendar_availability_service_too_long_for_working_hour(
    create_working_hours_list: Callable[[int], list[WorkingHourRead]],
    create_service: Callable[..., ServiceRead],
    session: Session,
    client: TestClient,
) -> None:
    service = create_service(
        duration_minutes=120,
        buffer_before_minutes=0,
        buffer_after_minutes=0,
    )
    working_hours = create_working_hours_list(3)

    middle_day = working_hours[1]

    working_hour = session.get(WorkingHour, middle_day.id)
    assert working_hour is not None

    working_hour.end_time = time(10, 0)
    session.add(working_hour)
    session.commit()

    response = client.get(
        "/appointments/availability/calendar",
        params={
            "from_date": working_hours[0].date.isoformat(),
            "to_date": working_hours[-1].date.isoformat(),
            "service_id": service.id,
        },
    )

    assert response.status_code == status.HTTP_200_OK

    expected_response = [
        {"date": working_hours[0].date.isoformat(), "available": True},
        {"date": working_hours[1].date.isoformat(), "available": False},
        {"date": working_hours[2].date.isoformat(), "available": True},
    ]

    assert response.json() == expected_response


@pytest.mark.parametrize(
    "from_offset, to_offset",
    [
        (-1, 5),  # Fecha inicial en el pasado
        (5, 3),  # Rango invertido
        (0, 31),  # Rango superior a 31 días
    ],
    ids=[
        "past_start_date",
        "inverted_date_range",
        "range_exceeds_31_days",
    ],
)
def test_calendar_availability_invalid_date_range(
    from_offset: int,
    to_offset: int,
    create_service: Callable[..., ServiceRead],
    client: TestClient,
    session: Session,
    ensure_business_settings: Callable[..., BusinessSettingsRead],
) -> None:
    ensure_business_settings()
    service = create_service()

    today = today = get_business_now(session).date()

    from_date = today + timedelta(days=from_offset)
    to_date = today + timedelta(days=to_offset)

    response = client.get(
        "/appointments/availability/calendar",
        params={
            "from_date": from_date.isoformat(),
            "to_date": to_date.isoformat(),
            "service_id": service.id,
        },
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.parametrize(
    "appointment_status, expected_availability",
    [
        (AppointmentStatusEnum.CONFIRMED, False),
        (AppointmentStatusEnum.PENDING_CONFIRMATION, False),
        (AppointmentStatusEnum.PENDING_PAYMENT, False),
        (AppointmentStatusEnum.COMPLETED, False),
        (AppointmentStatusEnum.CANCELLED_BY_CLIENT, True),
        (AppointmentStatusEnum.CANCELLED_BY_ADMIN, True),
        (AppointmentStatusEnum.NO_SHOW, True),
    ],
)
def test_calendar_availability_appointment_statuses(
    appointment_status: AppointmentStatusEnum,
    expected_availability: bool,
    create_working_hours_list: Callable[[int], list[WorkingHourRead]],
    create_service: Callable[..., ServiceRead],
    create_appointment: Callable[..., AppointmentRead],
    user_with_login: tuple[UserRead, str],
    session: Session,
    client: TestClient,
) -> None:
    service = create_service(
        duration_minutes=60,
        buffer_before_minutes=0,
        buffer_after_minutes=0,
    )
    working_hours = create_working_hours_list(3)
    user, _ = user_with_login

    business_settings = get_business_settings_or_409(session)

    middle_day = working_hours[1]

    first, last = calculate_first_and_last_possible_start(
        middle_day,
        service,
        business_settings,
    )

    step = timedelta(minutes=60)
    current = first

    while current <= last:
        create_appointment(
            user_id=user.id,
            service=service,
            starts_at=current.replace(tzinfo=None),
            status=appointment_status,
        )

        current += step

    response = client.get(
        "/appointments/availability/calendar",
        params={
            "from_date": working_hours[0].date.isoformat(),
            "to_date": working_hours[-1].date.isoformat(),
            "service_id": service.id,
        },
    )

    assert response.status_code == status.HTTP_200_OK

    expected_response = [
        {"date": working_hours[0].date.isoformat(), "available": True},
        {
            "date": working_hours[1].date.isoformat(),
            "available": expected_availability,
        },
        {"date": working_hours[2].date.isoformat(), "available": True},
    ]

    assert response.json() == expected_response


def test_calendar_availability_partially_blocked_day(
    create_working_hours_list: Callable[[int], list[WorkingHourRead]],
    create_service: Callable[..., ServiceRead],
    create_calendar_block: Callable[..., CalendarBlockRead],
    client: TestClient,
) -> None:
    service = create_service(
        duration_minutes=60,
        buffer_before_minutes=0,
        buffer_after_minutes=0,
    )
    working_hours = create_working_hours_list(3)

    middle_day = working_hours[1]

    starts_at = datetime.combine(
        middle_day.date,
        time(9, 0),
    )

    ends_at = datetime.combine(
        middle_day.date,
        time(12, 0),
    )

    create_calendar_block(
        starts_at=starts_at.isoformat(),
        ends_at=ends_at.isoformat(),
    )

    response = client.get(
        "/appointments/availability/calendar",
        params={
            "from_date": working_hours[0].date.isoformat(),
            "to_date": working_hours[-1].date.isoformat(),
            "service_id": service.id,
        },
    )

    assert response.status_code == status.HTTP_200_OK

    expected_response = [
        {"date": working_hours[0].date.isoformat(), "available": True},
        {"date": working_hours[1].date.isoformat(), "available": True},
        {"date": working_hours[2].date.isoformat(), "available": True},
    ]

    assert response.json() == expected_response


def test_calendar_availability_service_not_found(
    create_service: Callable[..., ServiceRead],
    ensure_business_settings: Callable[..., BusinessSettingsRead],
    client: TestClient,
) -> None:
    ensure_business_settings()
    service = create_service()

    nonexistent_service_id = service.id + 9999

    today = date.today()

    response = client.get(
        "/appointments/availability/calendar",
        params={
            "from_date": today.isoformat(),
            "to_date": (today + timedelta(days=2)).isoformat(),
            "service_id": nonexistent_service_id,
        },
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Servicio no encontrado"
