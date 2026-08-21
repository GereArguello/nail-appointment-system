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
