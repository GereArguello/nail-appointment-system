from collections.abc import Callable
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlmodel import Session, select

from app.core.config import settings
from app.core.datetime import as_utc
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
    """Genera una fecha y hora local para crear un bloqueo de calendario.

    Calcula una fecha relativa al día actual en la zona horaria del negocio
    utilizando days y establece la hora local indicada.

    Devuelve el datetime como cadena ISO 8601 sin información de zona horaria,
    tal como debe enviarse a la API.
    """
    tz = ZoneInfo(
        (timezone if timezone is not None else settings.BUSINESS_TIMEZONE).value
    )

    local_date = (datetime.now(tz) + timedelta(days=days)).date()

    local_datetime = datetime.combine(
        local_date,
        time(hour=hour),
    )

    return local_datetime.isoformat()


def local_naive_iso_as_utc(
    value: str,
    timezone: TimezoneEnum,
) -> datetime:
    """Interpreta un datetime ISO naive como horario local y lo convierte a UTC."""
    tz = ZoneInfo(timezone.value)

    local_datetime = datetime.fromisoformat(value).replace(tzinfo=tz)

    return local_datetime.astimezone(UTC)


def create_range_for_calendar_block(
    *,
    working_hour_date: date,
    starts_at: time,
    ends_at: time,
) -> tuple[str, str]:
    """Genera un intervalo local naive para un bloqueo de calendario.

    Combina la fecha laboral con las horas de inicio y finalización y devuelve
    ambos datetimes como cadenas ISO 8601 sin información de zona horaria.
    """
    start_datetime = datetime.combine(
        working_hour_date,
        starts_at,
    )

    end_datetime = datetime.combine(
        working_hour_date,
        ends_at,
    )

    return start_datetime.isoformat(), end_datetime.isoformat()


def get_local_date(
    days_offset: int = 0,
    timezone: TimezoneEnum | None = None,
) -> str:
    """Obtiene una fecha relativa al día actual en la zona horaria indicada.

    Utiliza la zona horaria configurada para el negocio si no se proporciona
    ninguna. Permite obtener fechas pasadas o futuras mediante days_offset.

    Devuelve la fecha como cadena en formato ISO 8601 (YYYY-MM-DD).
    """
    tz = ZoneInfo((timezone or settings.BUSINESS_TIMEZONE).value)

    return (datetime.now(tz) + timedelta(days=days_offset)).date().isoformat()


def as_local_naive(
    value: datetime,
    timezone: TimezoneEnum,
) -> datetime:
    return as_utc(value).astimezone(ZoneInfo(timezone)).replace(tzinfo=None)
