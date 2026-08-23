from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlmodel import select

from app.auth.dependencies import get_current_admin, get_current_user_optional
from app.calendar_blocks.models import CalendarBlock
from app.core.database import SessionDep
from app.core.date_ranges import date_range_as_datetime_utc, resolve_date_range
from app.core.enums import RoleEnum
from app.users.models import User
from app.utils import utc_now
from app.working_hours.models import WorkingHour
from app.working_hours.schemas import WorkingHourCreate, WorkingHourRead

router = APIRouter(prefix="/working-hours", tags=["working_hours"])


@router.post("/", response_model=WorkingHourRead, status_code=status.HTTP_201_CREATED)
def create_working_hour(
    session: SessionDep,
    data: WorkingHourCreate,
    current_admin: User = Depends(get_current_admin),
) -> WorkingHourRead:
    working_hours_data = data.model_dump()
    db_working_hours = WorkingHour(**working_hours_data)

    try:
        session.add(db_working_hours)
        session.commit()
        session.refresh(db_working_hours)
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un registro con este día",
        ) from exc

    response: WorkingHourRead = WorkingHourRead.model_validate(db_working_hours)

    return response


@router.get("/", response_model=list[WorkingHourRead], status_code=status.HTTP_200_OK)
def list_working_hours(
    session: SessionDep,
    current_user: User | None = Depends(get_current_user_optional),
    from_date: date | None = None,
    to_date: date | None = None,
) -> list[WorkingHourRead]:
    start_date, end_date = resolve_date_range(
        current_user=current_user,
        from_date=from_date,
        to_date=to_date,
    )

    statement = (
        select(WorkingHour)
        .where(
            WorkingHour.date >= start_date,
            WorkingHour.date <= end_date,
        )
        .order_by(WorkingHour.date)
    )

    return list(session.exec(statement).all())


@router.get(
    "/{working_hour_id}",
    response_model=WorkingHourRead,
    status_code=status.HTTP_200_OK,
)
def read_working_hour(
    session: SessionDep,
    working_hour_id: int,
    current_user: User | None = Depends(get_current_user_optional),
) -> WorkingHourRead:
    today = utc_now().date()

    query = select(WorkingHour).where(WorkingHour.id == working_hour_id)

    if not current_user or current_user.role != RoleEnum.ADMIN:
        query = query.where(WorkingHour.date >= today)

    working_hour = session.exec(query).first()

    if working_hour is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Fecha no encontrada"
        )

    response: WorkingHourRead = WorkingHourRead.model_validate(working_hour)

    return response


@router.delete("/{working_hour_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_working_hour(
    session: SessionDep,
    working_hour_id: int,
    current_admin: User = Depends(get_current_admin),
) -> None:
    working_hour = session.get(WorkingHour, working_hour_id)

    if not working_hour:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Horario laboral no encontrado",
        )

    now = utc_now()

    if working_hour.date < now.date() or (
        working_hour.date == now.date() and working_hour.start_time <= now.time()
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No se puede eliminar un horario laboral pasado o ya iniciado",
        )

    start_datetime, end_datetime = date_range_as_datetime_utc(
        working_hour.date,
        working_hour.date,
    )

    blocks = session.exec(
        select(CalendarBlock).where(
            CalendarBlock.starts_at >= start_datetime,
            CalendarBlock.starts_at <= end_datetime,
        )
    ).all()

    try:
        for block in blocks:
            session.delete(block)

        session.delete(working_hour)

        session.commit()

    except SQLAlchemyError:
        session.rollback()
        raise
