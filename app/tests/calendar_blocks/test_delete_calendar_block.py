from collections.abc import Callable
from datetime import timedelta

from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.calendar_blocks.models import CalendarBlock
from app.calendar_blocks.schemas import CalendarBlockRead
from app.core.datetime import utc_now
from app.users.schemas import UserRead


def test_delete_calendar_block_should_return_204(
    client: TestClient,
    session: Session,
    admin_with_login: tuple[UserRead, str],
    create_calendar_block: Callable[..., CalendarBlockRead],
) -> None:
    _, token = admin_with_login

    calendar_block = create_calendar_block()

    response = client.delete(
        f"/calendar-blocks/{calendar_block.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT

    deleted_block = session.get(CalendarBlock, calendar_block.id)

    assert deleted_block is None


def test_delete_calendar_block_should_return_404_when_not_found(
    client: TestClient,
    admin_with_login: tuple[UserRead, str],
) -> None:
    _, token = admin_with_login

    response = client.delete(
        "/calendar-blocks/999999",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_calendar_block_should_return_403_when_user_is_not_admin(
    client: TestClient,
    user_with_login: tuple[UserRead, str],
    create_calendar_block: Callable[..., CalendarBlockRead],
) -> None:
    _, token = user_with_login

    calendar_block = create_calendar_block()

    response = client.delete(
        f"/calendar-blocks/{calendar_block.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_delete_calendar_block_should_return_403_when_block_already_started(
    client: TestClient,
    session: Session,
    admin_with_login: tuple[UserRead, str],
    create_calendar_block: Callable[..., CalendarBlockRead],
) -> None:
    _, token = admin_with_login

    calendar_block = create_calendar_block()

    block = session.get(CalendarBlock, calendar_block.id)
    assert block is not None

    now = utc_now()

    block.starts_at = now - timedelta(minutes=30)
    block.ends_at = now + timedelta(minutes=30)

    session.commit()

    response = client.delete(
        f"/calendar-blocks/{calendar_block.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert (
        response.json()["detail"]
        == "No se puede eliminar un bloqueo pasado o ya iniciado"
    )

    existing_block = session.get(CalendarBlock, calendar_block.id)

    assert existing_block is not None


def test_delete_calendar_block_should_return_204_when_block_has_not_started(
    client: TestClient,
    session: Session,
    admin_with_login: tuple[UserRead, str],
    create_calendar_block: Callable[..., CalendarBlockRead],
) -> None:
    _, token = admin_with_login

    calendar_block = create_calendar_block()

    block = session.get(CalendarBlock, calendar_block.id)
    assert block is not None

    starts_at = utc_now() + timedelta(hours=1)
    ends_at = starts_at + timedelta(hours=1)

    block.starts_at = starts_at
    block.ends_at = ends_at

    session.add(block)
    session.commit()

    response = client.delete(
        f"/calendar-blocks/{calendar_block.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT

    deleted_block = session.get(CalendarBlock, calendar_block.id)

    assert deleted_block is None
