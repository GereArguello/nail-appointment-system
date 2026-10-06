from collections.abc import Callable
from datetime import datetime

from fastapi import status
from fastapi.testclient import TestClient

from app.business_settings.schemas import BusinessSettingsRead
from app.calendar_blocks.schemas import CalendarBlockRead
from app.core.datetime import parse_as_utc
from app.tests.helpers import local_naive_iso_as_utc, make_calendar_block_datetime
from app.users.schemas import UserRead
from app.working_hours.schemas import WorkingHourRead


def test_should_reject_calendar_block_with_timezone_aware_datetimes(
    client: TestClient,
    admin_with_login: tuple[UserRead, str],
) -> None:
    _, token = admin_with_login

    response = client.post(
        "/calendar-blocks/",
        json={
            "starts_at": "2026-10-02T13:00:00-03:00",
            "ends_at": "2026-10-02T15:00:00-03:00",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_should_create_calendar_block(
    client: TestClient,
    admin_with_login: tuple[UserRead, str],
    create_working_hours: Callable[..., WorkingHourRead],
    create_business_settings: Callable[..., BusinessSettingsRead],
) -> None:
    business_settings = create_business_settings()
    _, token = admin_with_login

    starts_at = make_calendar_block_datetime(
        days=1,
        hour=13,
        timezone=business_settings.timezone,
    )
    ends_at = make_calendar_block_datetime(
        days=1,
        hour=15,
        timezone=business_settings.timezone,
    )

    local_date = datetime.fromisoformat(starts_at).date()

    create_working_hours(
        date=local_date.isoformat(),
        start_time="09:00:00",
        end_time="18:00:00",
    )

    response = client.post(
        "/calendar-blocks/",
        json={
            "starts_at": starts_at,
            "ends_at": ends_at,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()

    expected_starts_at = local_naive_iso_as_utc(
        starts_at,
        business_settings.timezone,
    )
    expected_ends_at = local_naive_iso_as_utc(
        ends_at,
        business_settings.timezone,
    )

    assert parse_as_utc(data["starts_at"]) == expected_starts_at
    assert parse_as_utc(data["ends_at"]) == expected_ends_at
    assert data["reason"] is None


def test_should_reject_past_calendar_block(
    client: TestClient,
    admin_with_login: tuple[UserRead, str],
    create_business_settings: Callable[..., BusinessSettingsRead],
) -> None:
    business_settings = create_business_settings()
    _, token = admin_with_login

    starts_at = make_calendar_block_datetime(
        days=-1, hour=13, timezone=business_settings.timezone
    )

    ends_at = make_calendar_block_datetime(
        days=-1, hour=15, timezone=business_settings.timezone
    )

    response = client.post(
        "/calendar-blocks/",
        json={
            "starts_at": starts_at,
            "ends_at": ends_at,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_should_reject_calendar_block_when_end_is_before_start(
    client: TestClient,
    admin_with_login: tuple[UserRead, str],
    create_business_settings: Callable[..., BusinessSettingsRead],
) -> None:
    business_settings = create_business_settings()
    _, token = admin_with_login

    starts_at = make_calendar_block_datetime(
        days=1,
        hour=15,
        timezone=business_settings.timezone,
    )
    ends_at = make_calendar_block_datetime(
        days=1,
        hour=13,
        timezone=business_settings.timezone,
    )

    response = client.post(
        "/calendar-blocks/",
        json={
            "starts_at": starts_at,
            "ends_at": ends_at,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_should_reject_calendar_block_across_different_days(
    client: TestClient,
    admin_with_login: tuple[UserRead, str],
    create_business_settings: Callable[..., BusinessSettingsRead],
) -> None:
    business_settings = create_business_settings()
    _, token = admin_with_login

    starts_at = make_calendar_block_datetime(
        days=1,
        hour=22,
        timezone=business_settings.timezone,
    )
    ends_at = make_calendar_block_datetime(
        days=2,
        hour=2,
        timezone=business_settings.timezone,
    )

    response = client.post(
        "/calendar-blocks/",
        json={
            "starts_at": starts_at,
            "ends_at": ends_at,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_should_reject_overlapping_calendar_block(
    client: TestClient,
    admin_with_login: tuple[UserRead, str],
    create_calendar_block: Callable[..., CalendarBlockRead],
    create_business_settings: Callable[..., BusinessSettingsRead],
) -> None:
    business_settings = create_business_settings()
    _, token = admin_with_login

    create_calendar_block(
        starts_at=make_calendar_block_datetime(
            days=1,
            hour=13,
            timezone=business_settings.timezone,
        ),
        ends_at=make_calendar_block_datetime(
            days=1,
            hour=15,
            timezone=business_settings.timezone,
        ),
    )

    starts_at = make_calendar_block_datetime(
        days=1,
        hour=14,
        timezone=business_settings.timezone,
    )
    ends_at = make_calendar_block_datetime(
        days=1,
        hour=16,
        timezone=business_settings.timezone,
    )

    response = client.post(
        "/calendar-blocks/",
        json={"starts_at": starts_at, "ends_at": ends_at},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == (
        "El horario se superpone con otro bloqueo existente"
    )


def test_should_allow_adjacent_calendar_blocks(
    client: TestClient,
    admin_with_login: tuple[UserRead, str],
    create_calendar_block: Callable[..., CalendarBlockRead],
    create_business_settings: Callable[..., BusinessSettingsRead],
) -> None:
    business_settings = create_business_settings()
    _, token = admin_with_login

    create_calendar_block(
        starts_at=make_calendar_block_datetime(
            days=1,
            hour=13,
            timezone=business_settings.timezone,
        ),
        ends_at=make_calendar_block_datetime(
            days=1,
            hour=15,
            timezone=business_settings.timezone,
        ),
    )

    starts_at = make_calendar_block_datetime(
        days=1,
        hour=15,
        timezone=business_settings.timezone,
    )
    ends_at = make_calendar_block_datetime(
        days=1,
        hour=17,
        timezone=business_settings.timezone,
    )

    response = client.post(
        "/calendar-blocks/",
        json={"starts_at": starts_at, "ends_at": ends_at},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_201_CREATED


def test_should_reject_calendar_block_creation_without_authentication(
    client: TestClient,
    create_business_settings: Callable[..., BusinessSettingsRead],
) -> None:
    business_settings = create_business_settings()

    starts_at = make_calendar_block_datetime(
        days=1,
        hour=13,
        timezone=business_settings.timezone,
    )
    ends_at = make_calendar_block_datetime(
        days=1,
        hour=15,
        timezone=business_settings.timezone,
    )

    response = client.post(
        "/calendar-blocks/",
        json={"starts_at": starts_at, "ends_at": ends_at},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_should_reject_calendar_block_without_working_hour(
    client: TestClient,
    admin_with_login: tuple[UserRead, str],
    create_business_settings: Callable[..., BusinessSettingsRead],
) -> None:
    business_settings = create_business_settings()
    _, token = admin_with_login

    starts_at = make_calendar_block_datetime(
        days=1,
        hour=13,
        timezone=business_settings.timezone,
    )
    ends_at = make_calendar_block_datetime(
        days=1,
        hour=15,
        timezone=business_settings.timezone,
    )

    response = client.post(
        "/calendar-blocks/",
        json={
            "starts_at": starts_at,
            "ends_at": ends_at,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == (
        "No se puede bloquear un horario si no es día laborable"
    )


def test_should_reject_calendar_block_starting_before_working_hour(
    client: TestClient,
    admin_with_login: tuple[UserRead, str],
    create_working_hours: Callable[..., WorkingHourRead],
    create_business_settings: Callable[..., BusinessSettingsRead],
) -> None:
    business_settings = create_business_settings()
    _, token = admin_with_login

    starts_at = make_calendar_block_datetime(
        days=1,
        hour=8,
        timezone=business_settings.timezone,
    )
    ends_at = make_calendar_block_datetime(
        days=1,
        hour=10,
        timezone=business_settings.timezone,
    )

    local_date = datetime.fromisoformat(starts_at).date()

    create_working_hours(
        date=local_date.isoformat(),
        start_time="09:00:00",
        end_time="18:00:00",
    )

    response = client.post(
        "/calendar-blocks/",
        json={
            "starts_at": starts_at,
            "ends_at": ends_at,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_409_CONFLICT


def test_should_reject_calendar_block_ending_after_working_hour(
    client: TestClient,
    admin_with_login: tuple[UserRead, str],
    create_working_hours: Callable[..., WorkingHourRead],
    create_business_settings: Callable[..., BusinessSettingsRead],
) -> None:
    business_settings = create_business_settings()
    _, token = admin_with_login

    starts_at = make_calendar_block_datetime(
        days=1,
        hour=17,
        timezone=business_settings.timezone,
    )
    ends_at = make_calendar_block_datetime(
        days=1,
        hour=19,
        timezone=business_settings.timezone,
    )

    local_date = datetime.fromisoformat(starts_at).date()

    create_working_hours(
        date=local_date.isoformat(),
        start_time="09:00:00",
        end_time="18:00:00",
    )

    response = client.post(
        "/calendar-blocks/",
        json={
            "starts_at": starts_at,
            "ends_at": ends_at,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_409_CONFLICT


def test_should_allow_calendar_block_matching_working_hour_bounds(
    client: TestClient,
    admin_with_login: tuple[UserRead, str],
    create_working_hours: Callable[..., WorkingHourRead],
    create_business_settings: Callable[..., BusinessSettingsRead],
) -> None:
    business_settings = create_business_settings()
    _, token = admin_with_login

    starts_at = make_calendar_block_datetime(
        days=1,
        hour=9,
        timezone=business_settings.timezone,
    )
    ends_at = make_calendar_block_datetime(
        days=1,
        hour=18,
        timezone=business_settings.timezone,
    )

    local_date = datetime.fromisoformat(starts_at).date()

    create_working_hours(
        date=local_date.isoformat(),
        start_time="09:00:00",
        end_time="18:00:00",
    )

    response = client.post(
        "/calendar-blocks/",
        json={
            "starts_at": starts_at,
            "ends_at": ends_at,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_201_CREATED
