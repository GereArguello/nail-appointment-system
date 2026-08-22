from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.calendar_blocks.models import CalendarBlock
from app.calendar_blocks.schemas import CalendarBlockCreate
from app.working_hours.models import WorkingHour


def get_overlapping_block(
    session: Session, data: CalendarBlockCreate
) -> CalendarBlock | None:
    query = select(CalendarBlock).where(
        CalendarBlock.starts_at < data.ends_at,
        CalendarBlock.ends_at > data.starts_at,
    )

    existing_block: CalendarBlock | None = session.exec(query).first()

    return existing_block


def validate_calendar_block_creation(
    session: Session,
    data: CalendarBlockCreate,
) -> None:
    working_hour = session.exec(
        select(WorkingHour).where(
            WorkingHour.date == data.starts_at.date(),
            WorkingHour.start_time <= data.starts_at.time(),
            WorkingHour.end_time >= data.ends_at.time(),
        )
    ).first()

    if working_hour is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede bloquear un horario si no es día laborable",
        )

    existing_block = get_overlapping_block(session, data)

    if existing_block:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El horario se superpone con otro bloqueo existente",
        )
