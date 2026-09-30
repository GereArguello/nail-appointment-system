from collections.abc import Callable

from fastapi import status
from fastapi.testclient import TestClient

from app.business_settings.schemas import BusinessSettingsRead
from app.tests.utils import get_local_date
from app.users.schemas import UserRead
from app.working_hours.schemas import WorkingHourRead


def test_should_list_working_hours(
    client: TestClient,
    create_working_hours_list: Callable[[int], list[WorkingHourRead]],
    create_business_settings: Callable[..., BusinessSettingsRead],
) -> None:
    create_business_settings()
    created = create_working_hours_list(3)

    response = client.get("/working-hours/")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert len(data) == 3
    assert data == [working_hours.model_dump(mode="json") for working_hours in created]


def test_should_not_list_past_working_hours(
    client: TestClient,
    create_past_working_hours: Callable[..., WorkingHourRead],
    create_working_hours: Callable[..., WorkingHourRead],
    create_business_settings: Callable[..., BusinessSettingsRead],
) -> None:
    business_settings = create_business_settings()
    create_past_working_hours()

    future = create_working_hours(
        date=get_local_date(
            days_offset=1,
            timezone=business_settings.timezone,
        )
    )

    response = client.get("/working-hours/")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert len(data) == 1
    assert data[0] == future.model_dump(mode="json")


def test_should_return_empty_list_when_no_working_hours_exist(
    client: TestClient, create_business_settings: Callable[..., BusinessSettingsRead]
) -> None:
    create_business_settings()
    response = client.get("/working-hours/")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_should_list_working_hours_ordered_by_date(
    client: TestClient,
    create_working_hours: Callable[..., WorkingHourRead],
    create_business_settings: Callable[..., BusinessSettingsRead],
) -> None:
    business_settings = create_business_settings()
    timezone = business_settings.timezone

    create_working_hours(date=get_local_date(days_offset=3, timezone=timezone))
    create_working_hours(date=get_local_date(days_offset=1, timezone=timezone))
    create_working_hours(date=get_local_date(days_offset=2, timezone=timezone))

    response = client.get("/working-hours/")

    data = response.json()

    dates = [working_hours["date"] for working_hours in data]

    assert dates == sorted(dates)


def test_should_filter_working_hours_by_date_range(
    client: TestClient,
    create_working_hours_list: Callable[[int], list[WorkingHourRead]],
    create_business_settings: Callable[..., BusinessSettingsRead],
) -> None:
    create_business_settings()
    created = create_working_hours_list(5)

    response = client.get(
        "/working-hours/",
        params={
            "from_date": created[1].date,
            "to_date": created[3].date,
        },
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert data == [
        working_hour.model_dump(mode="json") for working_hour in created[1:4]
    ]


def test_should_reject_past_working_hours_range_for_non_admin(
    client: TestClient,
    create_past_working_hours: Callable[[], WorkingHourRead],
    user_with_login: tuple[UserRead, str],
    create_business_settings: Callable[..., BusinessSettingsRead],
) -> None:
    business_settings = create_business_settings()
    past = create_past_working_hours()

    _, token = user_with_login

    response = client.get(
        "/working-hours/",
        params={
            "from_date": past.date,
            "to_date": get_local_date(
                timezone=business_settings.timezone,
            ),
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_should_list_past_working_hours_as_admin(
    client: TestClient,
    create_past_working_hours: Callable[[], WorkingHourRead],
    admin_with_login: tuple[UserRead, str],
    create_business_settings: Callable[..., BusinessSettingsRead],
) -> None:
    business_settings = create_business_settings()
    past = create_past_working_hours()

    _, token = admin_with_login

    response = client.get(
        "/working-hours/",
        params={
            "from_date": past.date,
            "to_date": get_local_date(
                timezone=business_settings.timezone,
            ),
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert len(data) == 1
    assert data[0] == past.model_dump(mode="json")


def test_should_reject_working_hours_when_to_date_is_before_from_date(
    client: TestClient,
    create_business_settings: Callable[..., BusinessSettingsRead],
) -> None:
    business_settings = create_business_settings()
    timezone = business_settings.timezone

    response = client.get(
        "/working-hours/",
        params={
            "from_date": get_local_date(
                days_offset=5,
                timezone=timezone,
            ),
            "to_date": get_local_date(
                days_offset=1,
                timezone=timezone,
            ),
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_should_reject_working_hours_range_longer_than_31_days(
    client: TestClient,
    create_business_settings: Callable[..., BusinessSettingsRead],
) -> None:
    business_settings = create_business_settings()
    timezone = business_settings.timezone

    response = client.get(
        "/working-hours/",
        params={
            "from_date": get_local_date(timezone=timezone),
            "to_date": get_local_date(
                days_offset=32,
                timezone=timezone,
            ),
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
