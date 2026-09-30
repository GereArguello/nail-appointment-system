from collections.abc import Callable

from fastapi import status
from fastapi.testclient import TestClient

from app.business_settings.schemas import BusinessSettingsRead
from app.users.schemas import UserRead
from app.working_hours.models import WorkingHour
from app.working_hours.schemas import WorkingHourRead


def test_should_read_working_hour_by_id(
    client: TestClient,
    create_working_hours: Callable[..., WorkingHourRead],
    create_business_settings: Callable[..., BusinessSettingsRead],
) -> None:
    create_business_settings()
    working_hour = create_working_hours()

    response = client.get(f"/working-hours/{working_hour.id}")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert data["date"] == working_hour.date.isoformat()
    assert data["start_time"] == working_hour.start_time.isoformat()
    assert data["end_time"] == working_hour.end_time.isoformat()


def test_should_return_not_found_for_nonexistent_working_hour_id(
    client: TestClient, create_business_settings: Callable[..., BusinessSettingsRead]
) -> None:
    create_business_settings()
    response = client.get("/working-hours/999999")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Fecha no encontrada"


def test_should_return_not_found_for_past_working_hour(
    client: TestClient,
    create_past_working_hours: Callable[..., WorkingHour],
) -> None:
    past_working_hour = create_past_working_hours()

    response = client.get(f"/working-hours/{past_working_hour.id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Fecha no encontrada"


def test_should_read_past_working_hour_as_admin(
    client: TestClient,
    create_past_working_hours: Callable[..., WorkingHour],
    admin_with_login: tuple[UserRead, str],
) -> None:
    _, token = admin_with_login

    past_working_hour = create_past_working_hours()

    response = client.get(
        f"/working-hours/{past_working_hour.id}",
        headers={"Authorization": f"bearer {token}"},
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert data["date"] == past_working_hour.date.isoformat()
    assert data["start_time"] == past_working_hour.start_time.isoformat()
    assert data["end_time"] == past_working_hour.end_time.isoformat()
