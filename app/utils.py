from datetime import UTC, datetime


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
