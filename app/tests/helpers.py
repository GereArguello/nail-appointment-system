from collections.abc import Callable
from datetime import UTC, date, datetime, time, timedelta

from sqlmodel import Session, select

from app.utils import utc_now
from app.working_hours.models import WorkingHour
from app.working_hours.schemas import WorkingHourRead


def ensure_working_hour(
    session: Session,
    create_working_hours: Callable[..., WorkingHourRead],
    date: date,
) -> None:
    """Garantiza que exista un horario laboral para la fecha indicada"""
    existing = session.exec(select(WorkingHour).where(WorkingHour.date == date)).first()

    if existing is None:
        create_working_hours(
            date=date.isoformat(),
            start_time="09:00:00",
            end_time="18:00:00",
        )


def make_calendar_block_datetime(
    *,
    days: int = 1,
    hour: int,
) -> str:
    """Genera una fecha y hora en UTC como cadena ISO 8601."""
    return (
        utc_now().replace(hour=hour, minute=0, second=0, microsecond=0)
        + timedelta(days=days)
    ).isoformat()


def create_range_for_calendar_block(
    *, working_hour_date: date, starts_at: time, ends_at: time
) -> tuple[str, str]:
    """Genera el rango temporal de un bloqueo como cadenas ISO 8601 en UTC."""
    start_datetime = datetime.combine(
        working_hour_date, starts_at, tzinfo=UTC
    ).isoformat()
    end_datetime = datetime.combine(working_hour_date, ends_at, tzinfo=UTC).isoformat()

    return start_datetime, end_datetime
