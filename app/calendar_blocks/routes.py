from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select

from app.auth.dependencies import get_current_admin, get_current_user_optional
from app.calendar_blocks.models import CalendarBlock
from app.calendar_blocks.schemas import CalendarBlockCreate, CalendarBlockRead
from app.calendar_blocks.service import validate_calendar_block_creation
from app.core.database import SessionDep
from app.core.date_ranges import date_range_as_datetime_utc, resolve_date_range
from app.users.models import User
from app.utils import as_utc, utc_now

router = APIRouter(prefix="/calendar-blocks", tags=["calendar-blocks"])


@router.post("/", response_model=CalendarBlockRead, status_code=status.HTTP_201_CREATED)
def create_calendar_block(
    session: SessionDep,
    data: CalendarBlockCreate,
    current_admin: User = Depends(get_current_admin),
) -> CalendarBlockRead:

    validate_calendar_block_creation(session, data)

    db_calendar_block = CalendarBlock(**data.model_dump())

    session.add(db_calendar_block)
    session.commit()
    session.refresh(db_calendar_block)

    response: CalendarBlockRead = CalendarBlockRead.model_validate(db_calendar_block)

    return response


@router.get(
    "/",
    response_model=list[CalendarBlockRead],
    status_code=status.HTTP_200_OK,
)
def list_calendar_blocks(
    session: SessionDep,
    current_user: User | None = Depends(get_current_user_optional),
    from_date: date | None = None,
    to_date: date | None = None,
) -> list[CalendarBlockRead]:

    start_date, end_date = resolve_date_range(
        current_user=current_user,
        from_date=from_date,
        to_date=to_date,
    )

    start_datetime, end_datetime = date_range_as_datetime_utc(start_date, end_date)

    query = (
        select(CalendarBlock)
        .where(
            CalendarBlock.starts_at >= start_datetime,
            CalendarBlock.ends_at <= end_datetime,
        )
        .order_by(CalendarBlock.starts_at)
    )

    return list(session.exec(query).all())


@router.delete("/{calendar_block_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_calendar_block(
    session: SessionDep,
    calendar_block_id: int,
    current_admin: User = Depends(get_current_admin),
) -> None:
    block = session.get(CalendarBlock, calendar_block_id)

    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calendar block no encontrado",
        )

    starts_at = as_utc(block.starts_at)

    if starts_at <= utc_now():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No se puede eliminar un bloqueo pasado o ya iniciado",
        )

    session.delete(block)
    session.commit()
