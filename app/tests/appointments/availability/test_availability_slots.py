from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.business_settings.schemas import BusinessSettingsRead
from app.core.enums import TimezoneEnum
from app.services.schemas import ServiceRead
from app.working_hours.schemas import WorkingHourRead


def test_should_exclude_past_and_current_slots_for_today(
    client: TestClient,
    create_business_settings: Callable[..., BusinessSettingsRead],
    create_working_hours: Callable[..., WorkingHourRead],
    create_service: Callable[..., ServiceRead],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_business_settings(
        timezone=TimezoneEnum.BUENOS_AIRES,
        appointment_start_tolerance_minutes=0,
        appointment_end_tolerance_minutes=0,
    )

    working_hour = create_working_hours(
        start_time="09:00:00",
        end_time="12:00:00",
    )

    service = create_service(
        duration_minutes=60,
        buffer_before_minutes=0,
        buffer_after_minutes=0,
    )

    monkeypatch.setattr(
        "app.appointments.helper.utc_now",
        lambda: datetime(
            working_hour.date.year,
            working_hour.date.month,
            working_hour.date.day,
            13,
            30,
            tzinfo=UTC,
        ),
    )

    response = client.get(
        "/appointments/availability",
        params={
            "target_date": working_hour.date,
            "service_id": service.id,
        },
    )

    assert response.status_code == status.HTTP_200_OK

    assert response.json() == [
        f"{working_hour.date}T10:45:00",
        f"{working_hour.date}T11:00:00",
    ]


def test_should_not_filter_slots_by_current_time_for_future_date(
    client: TestClient,
    create_business_settings: Callable[..., BusinessSettingsRead],
    create_working_hours: Callable[..., WorkingHourRead],
    create_service: Callable[..., ServiceRead],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_business_settings(
        timezone=TimezoneEnum.BUENOS_AIRES,
        appointment_start_tolerance_minutes=0,
        appointment_end_tolerance_minutes=0,
    )

    working_hour = create_working_hours(
        days=1,
        start_time="09:00:00",
        end_time="12:00:00",
    )

    service = create_service(
        duration_minutes=60,
        buffer_before_minutes=0,
        buffer_after_minutes=0,
    )

    target_date = working_hour.date

    monkeypatch.setattr(
        "app.appointments.routes.utc_now",
        lambda: datetime(
            target_date.year,
            target_date.month,
            target_date.day - 1,
            16,
            0,
            tzinfo=UTC,
        ),
    )

    response = client.get(
        "/appointments/availability",
        params={
            "target_date": target_date,
            "service_id": service.id,
        },
    )

    assert response.status_code == status.HTTP_200_OK

    assert response.json() == [
        f"{target_date}T09:00:00",
        f"{target_date}T09:15:00",
        f"{target_date}T09:30:00",
        f"{target_date}T09:45:00",
        f"{target_date}T10:00:00",
        f"{target_date}T10:15:00",
        f"{target_date}T10:30:00",
        f"{target_date}T10:45:00",
        f"{target_date}T11:00:00",
    ]
