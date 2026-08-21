from collections.abc import Callable

from fastapi import status
from fastapi.testclient import TestClient

from app.calendar_blocks.schemas import CalendarBlockRead
from app.tests.calendar_blocks.helpers import make_calendar_block_datetime, parse_as_utc
from app.users.schemas import UserRead


def test_should_create_calendar_block(
    client: TestClient, admin_with_login: tuple[UserRead, str]
) -> None:
    _, token = admin_with_login

    starts_at = make_calendar_block_datetime(days=1, hour=13)
    ends_at = make_calendar_block_datetime(days=1, hour=15)

    response = client.post(
        "/calendar-blocks/",
        json={"starts_at": starts_at, "ends_at": ends_at},
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
