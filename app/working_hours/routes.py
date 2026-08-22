from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app.auth.dependencies import get_current_admin, get_current_user_optional
from app.core.database import SessionDep
from app.core.enums import RoleEnum
from app.users.models import User
from app.utils import utc_now
from app.working_hours.models import WorkingHour
from app.working_hours.schemas import WorkingHourCreate, WorkingHourRead

router = APIRouter(prefix="/working-hours", tags=["working_hours"])


@router.post("/", response_model=WorkingHourRead, status_code=status.HTTP_201_CREATED)
def create_working_hours(
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
def list_working_hours(session: SessionDep) -> list[WorkingHourRead]:
    today = utc_now().date()

    statement = (
        select(WorkingHour).where(WorkingHour.date >= today).order_by(WorkingHour.date)
    )

    working_hours = session.exec(statement).all()

    return [
        WorkingHourRead.model_validate(working_hour) for working_hour in working_hours
    ]


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
