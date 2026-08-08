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
