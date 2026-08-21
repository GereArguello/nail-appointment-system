from datetime import UTC, datetime, timedelta

from app.utils import utc_now


def make_calendar_block_datetime(
    *,
    days: int = 1,
    hour: int,
) -> str:
    return (
        utc_now().replace(hour=hour, minute=0, second=0, microsecond=0)
        + timedelta(days=days)
    ).isoformat()


def parse_as_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)

    return parsed.astimezone(UTC)
