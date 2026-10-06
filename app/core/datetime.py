from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from app.core.enums import TimezoneEnum


def utc_now() -> datetime:
    return datetime.now(UTC)


def as_utc(value: datetime) -> datetime:
    """Convierte un datetime a UTC.

    Si el datetime no tiene zona horaria, se asume que ya representa
    una fecha y hora en UTC. Si tiene zona horaria, se convierte a UTC.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)

    return value.astimezone(UTC)


def parse_as_utc(value: str) -> datetime:
    """Convierte una fecha en formato ISO 8601 a un datetime en UTC."""
    return as_utc(datetime.fromisoformat(value))


def get_now_in_timezone(timezone: TimezoneEnum) -> datetime:
    """Obtiene el instante actual expresado en la zona horaria indicada.

    Convierte la hora actual UTC a la zona horaria proporcionada,
    conservando el mismo instante absoluto.
    """
    return utc_now().astimezone(ZoneInfo(timezone))


def get_today_in_timezone(timezone: TimezoneEnum) -> date:
    """Obtiene la fecha actual según la zona horaria indicada.

    Devuelve únicamente la fecha local, sin información horaria.
    """
    return get_now_in_timezone(timezone).date()


def localize_business_datetime(
    value: datetime,
    timezone: TimezoneEnum,
) -> datetime:
    """Interpreta o convierte un datetime a la zona horaria del negocio.

    Si el datetime ya contiene información de zona horaria, lo convierte a la
    zona indicada preservando el instante que representa.

    Si el datetime es naive, lo interpreta como una fecha y hora local del
    negocio y le asigna directamente la zona horaria indicada.
    """
    if value.tzinfo is not None and value.utcoffset() is not None:
        return value.astimezone(ZoneInfo(timezone))

    return value.replace(tzinfo=ZoneInfo(timezone))
