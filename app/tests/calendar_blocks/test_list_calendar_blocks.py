from collections.abc import Callable
from datetime import timedelta

from fastapi import status
from fastapi.testclient import TestClient

from app.calendar_blocks.schemas import CalendarBlockRead
from app.users.schemas import UserRead
from app.utils import utc_now


def test_should_return_calendar_block_list(
    client: TestClient,
    create_calendar_block_list: Callable[[int], list[CalendarBlockRead]],
) -> None:
    created = create_calendar_block_list(3)

    response = client.get("/calendar-blocks/")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert len(data) == 3
    assert data == [
        calendar_block.model_dump(mode="json") for calendar_block in created
    ]


def test_should_list_past_calendar_blocks_as_admin(
    client: TestClient,
    create_calendar_block_list: Callable[[int], list[CalendarBlockRead]],
    create_past_calendar_block: Callable[..., CalendarBlockRead],
    admin_with_login: tuple[UserRead, str],
) -> None:
    future = create_calendar_block_list(5)
    past = create_past_calendar_block()

    from_date = past.starts_at.date()
    to_date = future[-1].ends_at.date()

    _, token = admin_with_login

    response = client.get(
        "/calendar-blocks/",
        params={
            "from_date": from_date,
            "to_date": to_date,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_200_OK


def test_should_reject_past_calendar_blocks_range_for_non_admin(
    client: TestClient,
    create_calendar_block_list: Callable[[int], list[CalendarBlockRead]],
    create_past_calendar_block: Callable[..., CalendarBlockRead],
    user_with_login: tuple[UserRead, str],
) -> None:
    future = create_calendar_block_list(5)
    past = create_past_calendar_block()

    from_date = past.starts_at.date()
    to_date = future[-1].ends_at.date()

    _, token = user_with_login

    response = client.get(
        "/calendar-blocks/",
        params={
            "from_date": from_date,
            "to_date": to_date,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "Solo administradores pueden ver fechas pasadas"


def test_should_reject_when_to_date_is_before_from_date(
    client: TestClient,
) -> None:
    today = utc_now().date()

    response = client.get(
        "/calendar-blocks/",
        params={
            "from_date": today + timedelta(days=5),
            "to_date": today + timedelta(days=1),
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert (
        response.json()["detail"] == "La fecha final no puede ser anterior a la inicial"
    )


def test_should_reject_range_longer_than_31_days(
    client: TestClient,
) -> None:
    today = utc_now().date()

    response = client.get(
        "/calendar-blocks/",
        params={
            "from_date": today,
            "to_date": today + timedelta(days=32),
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "El rango no puede superar los 31 días"


def test_should_list_future_calendar_blocks_for_non_admin(
    client: TestClient,
    create_calendar_block_list: Callable[[int], list[CalendarBlockRead]],
    user_with_login: tuple[UserRead, str],
) -> None:
    created = create_calendar_block_list(5)

    _, token = user_with_login

    response = client.get(
        "/calendar-blocks/",
        params={
            "from_date": created[0].starts_at.date(),
            "to_date": created[-1].ends_at.date(),
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert len(data) == 5
