from datetime import date, datetime, timedelta
from typing import Any

from app.tests.helpers import make_calendar_block_datetime
from app.utils import utc_now


def create_data(**overrides: Any) -> dict[str, Any]:
    data = {
        "first_name": "Karla",
        "last_name": "Ficticio",
        "email": "test@example.com",
        "password": "A12345678",
        "password2": "A12345678",
        "birth_date": date(2000, 1, 1).isoformat(),
    }

    data.update(overrides)
    return data


def create_service_data(**overrides: Any) -> dict[str, Any]:
    data = {
        "name": "Manicura clásica",
        "description": "Servicio de manicura clásica",
        "duration_minutes": 60,
        "buffer_before_minutes": 10,
        "buffer_after_minutes": 10,
        "price": 400,
        "deposit_amount": 0,
    }
    data.update(overrides)
    return data


def create_working_hours_data(**overrides: Any) -> dict[str, Any]:
    date = (utc_now() + timedelta(days=5)).date().isoformat()

    data = {"date": date, "start_time": "09:00:00", "end_time": "18:00:00"}

    data.update(overrides)

    return data


def create_calendar_block_data(**overrides: Any) -> dict[str, Any]:

    starts_at = make_calendar_block_datetime(days=1, hour=13)
    ends_at = make_calendar_block_datetime(days=1, hour=15)

    data = {"starts_at": starts_at, "ends_at": ends_at}

    data.update(overrides)

    return data


def create_business_settings_data(**overrides: Any) -> dict[str, Any]:

    data = {
        "appointment_start_tolerance_minutes": 10,
        "appointment_end_tolerance_minutes": 10,
        "deposit_payment_expiration_hours": 24,
    }

    data.update(overrides)

    return data


def create_appointment_data(
    service_id: int,
    starts_at: datetime,
    **overrides: Any,
) -> dict[str, Any]:
    data = {
        "service_id": service_id,
        "starts_at": starts_at.isoformat(),
        "description": "Diseño francés con detalles dorados",
    }

    data.update(overrides)

    return data
