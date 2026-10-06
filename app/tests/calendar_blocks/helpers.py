from datetime import timedelta

from app.core.datetime import utc_now


def make_calendar_block_datetime(
    *,
    days: int = 1,
    hour: int,
) -> str:
    return (
        utc_now().replace(hour=hour, minute=0, second=0, microsecond=0)
        + timedelta(days=days)
    ).isoformat()
