from datetime import date
from typing import Any


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
