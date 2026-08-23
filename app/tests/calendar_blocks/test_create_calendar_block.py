from collections.abc import Callable

from fastapi import status
from fastapi.testclient import TestClient

from app.calendar_blocks.schemas import CalendarBlockRead
from app.tests.calendar_blocks.helpers import make_calendar_block_datetime
from app.users.schemas import UserRead
from app.utils import parse_as_utc
from app.working_hours.schemas import WorkingHourRead


def test_should_create_calendar_block(
    client: TestClient,
    admin_with_login: tuple[UserRead, str],
    create_working_hours: Callable[..., WorkingHourRead],
) -> None:
    _, token = admin_with_login

    starts_at = make_calendar_block_datetime(days=1, hour=13)
    ends_at = make_calendar_block_datetime(days=1, hour=15)

    create_working_hours(
        date=parse_as_utc(starts_at).date().isoformat(),
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

    assert parse_as_utc(data["starts_at"]) == parse_as_utc(starts_at)
    assert parse_as_utc(data["ends_at"]) == parse_as_utc(ends_at)
    assert data["reason"] is None


def test_should_reject_past_calendar_block(
    client: TestClient,
    admin_with_login: tuple[UserRead, str],
) -> None:
    _, token = admin_with_login

    starts_at = make_calendar_block_datetime(days=-1, hour=13)
    ends_at = make_calendar_block_datetime(days=-1, hour=15)

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
) -> None:
    _, token = admin_with_login

    starts_at = make_calendar_block_datetime(days=1, hour=15)
    ends_at = make_calendar_block_datetime(days=1, hour=13)

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
) -> None:
    _, token = admin_with_login

    starts_at = make_calendar_block_datetime(days=1, hour=22)
    ends_at = make_calendar_block_datetime(days=2, hour=2)

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
) -> None:
    _, token = admin_with_login

    create_calendar_block(
        starts_at=make_calendar_block_datetime(days=1, hour=13),
        ends_at=make_calendar_block_datetime(days=1, hour=15),
    )

    starts_at = make_calendar_block_datetime(days=1, hour=14)
    ends_at = make_calendar_block_datetime(days=1, hour=16)

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
) -> None:
    _, token = admin_with_login

    create_calendar_block(
        starts_at=make_calendar_block_datetime(days=1, hour=13),
        ends_at=make_calendar_block_datetime(days=1, hour=15),
    )

    starts_at = make_calendar_block_datetime(days=1, hour=15)
    ends_at = make_calendar_block_datetime(days=1, hour=17)

    response = client.post(
        "/calendar-blocks/",
        json={"starts_at": starts_at, "ends_at": ends_at},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_201_CREATED


def test_should_reject_calendar_block_creation_without_authentication(
    client: TestClient,
) -> None:
    starts_at = make_calendar_block_datetime(days=1, hour=13)
    ends_at = make_calendar_block_datetime(days=1, hour=15)

    response = client.post(
        "/calendar-blocks/",
        json={"starts_at": starts_at, "ends_at": ends_at},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_should_reject_calendar_block_without_working_hour(
    client: TestClient,
    admin_with_login: tuple[UserRead, str],
) -> None:
    _, token = admin_with_login

    starts_at = make_calendar_block_datetime(days=1, hour=13)
    ends_at = make_calendar_block_datetime(days=1, hour=15)

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
) -> None:
    _, token = admin_with_login

    starts_at = make_calendar_block_datetime(days=1, hour=8)
    ends_at = make_calendar_block_datetime(days=1, hour=10)

    create_working_hours(
        date=parse_as_utc(starts_at).date().isoformat(),
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
) -> None:
    _, token = admin_with_login

    starts_at = make_calendar_block_datetime(days=1, hour=17)
    ends_at = make_calendar_block_datetime(days=1, hour=19)

    create_working_hours(
        date=parse_as_utc(starts_at).date().isoformat(),
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
) -> None:
    _, token = admin_with_login

    starts_at = make_calendar_block_datetime(days=1, hour=9)
    ends_at = make_calendar_block_datetime(days=1, hour=18)

    create_working_hours(
        date=parse_as_utc(starts_at).date().isoformat(),
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
