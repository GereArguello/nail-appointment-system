from collections.abc import Callable
from datetime import timedelta

from fastapi import status
from fastapi.testclient import TestClient

from app.utils import utc_now
from app.working_hours.models import WorkingHours
from app.working_hours.schemas import WorkingHoursRead


def test_should_list_working_hours(
    client: TestClient,
    create_working_hours_list: Callable[[int], list[WorkingHoursRead]],
) -> None:
    created = create_working_hours_list(3)

    response = client.get("/working-hours/")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert len(data) == 3
    assert data == [working_hours.model_dump(mode="json") for working_hours in created]


def test_should_not_list_past_working_hours(
    client: TestClient,
    create_past_working_hours: Callable[..., WorkingHours],
    create_working_hours: Callable[..., WorkingHoursRead],
) -> None:
    create_past_working_hours()

    future = create_working_hours(
        date=(utc_now() + timedelta(days=1)).date().isoformat()
    )

    response = client.get("/working-hours/")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert len(data) == 1
    assert data[0] == future.model_dump(mode="json")


def test_should_return_empty_list_when_no_working_hours_exist(
    client: TestClient,
) -> None:
    response = client.get("/working-hours/")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_should_list_working_hours_ordered_by_date(
    client: TestClient,
    create_working_hours: Callable[..., WorkingHoursRead],
) -> None:
    create_working_hours(date=(utc_now() + timedelta(days=3)).date().isoformat())
    create_working_hours(date=(utc_now() + timedelta(days=1)).date().isoformat())
    create_working_hours(date=(utc_now() + timedelta(days=2)).date().isoformat())

    response = client.get("/working-hours/")

    data = response.json()

    dates = [working_hours["date"] for working_hours in data]

    assert dates == sorted(dates)
