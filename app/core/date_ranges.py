from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status

from app.core.datetime import get_today_in_timezone
from app.core.enums import TimezoneEnum


def resolve_date_range(
    *,
    from_date: date | None,
    to_date: date | None,
    timezone: TimezoneEnum,
) -> tuple[date, date, date]:
    today = get_today_in_timezone(timezone)

    start_date = from_date or today
    end_date = to_date or start_date + timedelta(days=30)

    if end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La fecha final no puede ser anterior a la inicial",
        )

    if end_date - start_date > timedelta(days=30):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El rango no puede superar los 31 días",
        )

    return start_date, end_date, today


def date_range_as_datetime_utc(
    start_date: date,
    end_date: date,
    timezone: TimezoneEnum,
) -> tuple[datetime, datetime]:
    """Convierte un rango de fechas locales del negocio a límites UTC."""
    zone = ZoneInfo(timezone)

    start_local = datetime.combine(
        start_date,
        time.min,
        tzinfo=zone,
    )

    end_local = datetime.combine(
        end_date + timedelta(days=1),
        time.min,
        tzinfo=zone,
    )

    return (
        start_local.astimezone(UTC),
        end_local.astimezone(UTC),
    )
