from collections.abc import Callable
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.business_settings.schemas import BusinessSettingsRead
from app.calendar_blocks.models import CalendarBlock
from app.calendar_blocks.schemas import CalendarBlockRead
from app.tests.helpers import (
    create_range_for_calendar_block,
    make_calendar_block_datetime,
)
from app.users.schemas import UserRead
from app.utils import as_utc
from app.working_hours.models import WorkingHour
from app.working_hours.schemas import WorkingHourRead


def test_delete_working_hour_should_return_204(
    client: TestClient,
    session: Session,
    admin_with_login: tuple[UserRead, str],
    create_working_hours: Callable[..., WorkingHourRead],
    create_business_settings: Callable[..., BusinessSettingsRead],
) -> None:
    create_business_settings()
    _, token = admin_with_login

    working_hour = create_working_hours()

    response = client.delete(
        f"/working-hours/{working_hour.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT

    deleted_working_hour = session.get(WorkingHour, working_hour.id)

    assert deleted_working_hour is None


def test_delete_working_hour_should_return_404_when_not_found(
    client: TestClient,
    admin_with_login: tuple[UserRead, str],
) -> None:
    _, token = admin_with_login

    response = client.delete(
        "/working-hours/999999",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Horario laboral no encontrado"


def test_delete_working_hour_should_return_403_when_user_is_not_admin(
    client: TestClient,
    user_with_login: tuple[UserRead, str],
    create_working_hours: Callable[..., WorkingHourRead],
    create_business_settings: Callable[..., BusinessSettingsRead],
) -> None:
    create_business_settings()
    _, token = user_with_login

    working_hour = create_working_hours()

    response = client.delete(
        f"/working-hours/{working_hour.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_delete_working_hour_should_return_403_when_working_hour_already_started(
    client: TestClient,
    session: Session,
    admin_with_login: tuple[UserRead, str],
    create_working_hours: Callable[..., WorkingHourRead],
    create_business_settings: Callable[..., BusinessSettingsRead],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    business_settings = create_business_settings()

    _, token = admin_with_login

    working_hour = create_working_hours()

    now = datetime(
        2026,
        10,
        15,
        12,
        0,
        tzinfo=ZoneInfo(business_settings.timezone.value),
    )

    monkeypatch.setattr(
        "app.working_hours.routes.get_now_in_timezone",
        lambda timezone: now,
    )

    stored_working_hour = session.get(WorkingHour, working_hour.id)
    assert stored_working_hour is not None

    stored_working_hour.date = now.date()
    stored_working_hour.start_time = (now - timedelta(hours=1)).time()

    stored_working_hour.end_time = (now + timedelta(hours=1)).time()

    session.add(stored_working_hour)
    session.commit()

    response = client.delete(
        f"/working-hours/{working_hour.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert (
        response.json()["detail"]
        == "No se puede eliminar un horario laboral pasado o ya iniciado"
    )

    existing_working_hour = session.get(WorkingHour, working_hour.id)

    assert existing_working_hour is not None


def test_delete_working_hour_should_delete_calendar_blocks_from_same_day(
    client: TestClient,
    session: Session,
    admin_with_login: tuple[UserRead, str],
    create_working_hours: Callable[..., WorkingHourRead],
    create_calendar_block: Callable[..., CalendarBlockRead],
    create_business_settings: Callable[..., BusinessSettingsRead],
) -> None:
    business_settings = create_business_settings()
    _, token = admin_with_login

    working_hour = create_working_hours()

    starts_at, ends_at = create_range_for_calendar_block(
        working_hour_date=working_hour.date,
        starts_at=time(10, 0),
        ends_at=time(11, 0),
        timezone=business_settings.timezone,
    )

    block_1 = create_calendar_block(
        starts_at=starts_at,
        ends_at=ends_at,
    )

    starts_at, ends_at = create_range_for_calendar_block(
        working_hour_date=working_hour.date,
        starts_at=time(12, 0),
        ends_at=time(13, 0),
        timezone=business_settings.timezone,
    )

    block_2 = create_calendar_block(
        starts_at=starts_at,
        ends_at=ends_at,
    )

    response = client.delete(
        f"/working-hours/{working_hour.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT

    assert session.get(WorkingHour, working_hour.id) is None
    assert session.get(CalendarBlock, block_1.id) is None
    assert session.get(CalendarBlock, block_2.id) is None


def test_delete_working_hour_should_not_delete_calendar_blocks_from_other_days(
    client: TestClient,
    session: Session,
    admin_with_login: tuple[UserRead, str],
    create_calendar_block: Callable[..., CalendarBlockRead],
    create_business_settings: Callable[..., BusinessSettingsRead],
) -> None:
    business_settings = create_business_settings()
    _, token = admin_with_login

    block_same_day = create_calendar_block(
        starts_at=make_calendar_block_datetime(
            days=1,
            hour=10,
            timezone=business_settings.timezone,
        ),
        ends_at=make_calendar_block_datetime(
            days=1,
            hour=11,
            timezone=business_settings.timezone,
        ),
    )

    other_block = create_calendar_block(
        starts_at=make_calendar_block_datetime(
            days=2, hour=10, timezone=business_settings.timezone
        ),
        ends_at=make_calendar_block_datetime(
            days=2, hour=11, timezone=business_settings.timezone
        ),
    )

    tz = ZoneInfo(business_settings.timezone.value)

    first_date = as_utc(block_same_day.starts_at).astimezone(tz).date()

    other_date = as_utc(other_block.starts_at).astimezone(tz).date()

    working_hour = session.exec(
        select(WorkingHour).where(WorkingHour.date == first_date)
    ).first()

    other_working_hour = session.exec(
        select(WorkingHour).where(WorkingHour.date == other_date)
    ).first()

    assert working_hour is not None
    assert other_working_hour is not None

    response = client.delete(
        f"/working-hours/{working_hour.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT

    assert session.get(WorkingHour, working_hour.id) is None
    assert session.get(CalendarBlock, block_same_day.id) is None

    assert session.get(WorkingHour, other_working_hour.id) is not None
    assert session.get(CalendarBlock, other_block.id) is not None
