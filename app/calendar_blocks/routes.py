from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select

from app.auth.dependencies import get_current_admin, get_current_user_optional
from app.calendar_blocks.models import CalendarBlock
from app.calendar_blocks.schemas import CalendarBlockCreate, CalendarBlockRead
from app.calendar_blocks.service import (
    date_range_as_datetime_utc,
    get_overlapping_block,
)
from app.core.database import SessionDep
from app.core.enums import RoleEnum
from app.users.models import User
from app.utils import utc_now

router = APIRouter(prefix="/calendar-blocks", tags=["calendar-blocks"])


@router.post("/", response_model=CalendarBlockRead, status_code=status.HTTP_201_CREATED)
def create_calendar_block(
    session: SessionDep,
    data: CalendarBlockCreate,
    current_admin: User = Depends(get_current_admin),
) -> CalendarBlockRead:

    existing_block = get_overlapping_block(session, data)

    if existing_block:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El horario se superpone con otro bloqueo existente",
        )

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

    today = utc_now().date()
    is_admin = current_user is not None and current_user.role == RoleEnum.ADMIN

    # Si no se especifica comienzo, empieza hoy
    start_date = from_date or today

    # Si no se especifica final, consulta 31 días
    end_date = to_date or start_date + timedelta(days=31)

    # Solo admins pueden consultar períodos pasados
    if start_date < today and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo administradores pueden ver fechas pasadas",
        )

    # El final no puede ser anterior al comienzo
    if end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La fecha final no puede ser anterior a la inicial",
        )

    # Limitar el rango
    if end_date - start_date > timedelta(days=31):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El rango no puede superar los 31 días",
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
