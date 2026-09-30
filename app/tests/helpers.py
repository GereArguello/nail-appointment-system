from collections.abc import Callable
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlmodel import Session, select

from app.core.config import settings
from app.core.enums import TimezoneEnum
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
    timezone: TimezoneEnum | None = None,
) -> str:
    """Genera una fecha y hora para un bloqueo de calendario.

    Calcula una fecha relativa al día actual en la zona horaria del negocio
    utilizando days y establece la hora local indicada.

    Convierte el resultado a UTC y lo devuelve como cadena ISO 8601.
    """
    tz = ZoneInfo(
        (timezone if timezone is not None else settings.BUSINESS_TIMEZONE).value
    )

    local_date = (datetime.now(tz) + timedelta(days=days)).date()

    local_datetime = datetime.combine(
        local_date,
        time(hour=hour),
        tzinfo=tz,
    )

    return local_datetime.astimezone(UTC).isoformat()


def create_range_for_calendar_block(
    *,
    working_hour_date: date,
    starts_at: time,
    ends_at: time,
    timezone: TimezoneEnum,
) -> tuple[str, str]:
    """Genera un intervalo temporal para un bloqueo de calendario.

    Combina la fecha laboral con las horas locales de inicio y finalización,
    interpretándolas según la zona horaria del negocio.

    Convierte ambos extremos a UTC y devuelve una tupla de cadenas
    ISO 8601 con el inicio y la finalización del intervalo.
    """

    tz = ZoneInfo(timezone.value)

    start_datetime = datetime.combine(
        working_hour_date,
        starts_at,
        tzinfo=tz,
    ).astimezone(UTC)

    end_datetime = datetime.combine(
        working_hour_date,
        ends_at,
        tzinfo=tz,
    ).astimezone(UTC)

    return start_datetime.isoformat(), end_datetime.isoformat()
