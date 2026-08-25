from collections.abc import Callable

from fastapi import status
from fastapi.testclient import TestClient

from app.calendar_blocks.schemas import CalendarBlockRead
from app.users.schemas import UserRead


def test_should_read_calendar_block(
    client: TestClient,
    create_calendar_block: Callable[..., CalendarBlockRead],
) -> None:
    calendar_block = create_calendar_block()

    response = client.get(f"/calendar-blocks/{calendar_block.id}")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert data == calendar_block.model_dump(mode="json")


def test_should_return_404_when_calendar_block_does_not_exist(
    client: TestClient,
) -> None:
    response = client.get("/calendar-blocks/999999")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Bloqueo no encontrado"


def test_should_not_read_past_calendar_block(
    client: TestClient,
    create_past_calendar_block: Callable[..., CalendarBlockRead],
) -> None:
    calendar_block = create_past_calendar_block()

    response = client.get(f"/calendar-blocks/{calendar_block.id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Bloqueo no encontrado"


def test_should_read_past_calendar_block_as_admin(
    client: TestClient,
    admin_with_login: tuple[UserRead, str],
    create_past_calendar_block: Callable[..., CalendarBlockRead],
) -> None:
    _, token = admin_with_login
    calendar_block = create_past_calendar_block()

    response = client.get(
        f"/calendar-blocks/{calendar_block.id}",
        headers={"Authorization": f"bearer {token}"},
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert data == calendar_block.model_dump(mode="json")
