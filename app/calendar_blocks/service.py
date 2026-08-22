from datetime import UTC, date, datetime, time

from sqlmodel import Session, select

from app.calendar_blocks.models import CalendarBlock
from app.calendar_blocks.schemas import CalendarBlockCreate


def get_overlapping_block(
    session: Session, data: CalendarBlockCreate
) -> CalendarBlock | None:
    query = select(CalendarBlock).where(
        CalendarBlock.starts_at < data.ends_at,
        CalendarBlock.ends_at > data.starts_at,
    )

    existing_block: CalendarBlock | None = session.exec(query).first()

    return existing_block


def date_range_as_datetime_utc(
    start_date: date,
    end_date: date,
) -> tuple[datetime, datetime]:
    start_datetime = datetime.combine(start_date, time.min, tzinfo=UTC)
    end_datetime = datetime.combine(end_date, time.max, tzinfo=UTC)

    return start_datetime, end_datetime
