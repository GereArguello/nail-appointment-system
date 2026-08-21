from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app.auth.dependencies import get_current_admin, get_current_user_optional
from app.core.database import SessionDep
from app.core.enums import RoleEnum
from app.users.models import User
from app.utils import utc_now
from app.working_hours.models import WorkingHours
from app.working_hours.schemas import WorkingHoursCreate, WorkingHoursRead

router = APIRouter(prefix="/working-hours", tags=["working_hours"])


@router.post("/", response_model=WorkingHoursRead, status_code=status.HTTP_201_CREATED)
def create_working_hours(
    session: SessionDep,
    data: WorkingHoursCreate,
    current_admin: User = Depends(get_current_admin),
) -> WorkingHoursRead:
    working_hours_data = data.model_dump()
    db_working_hours = WorkingHours(**working_hours_data)

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

    response: WorkingHoursRead = WorkingHoursRead.model_validate(db_working_hours)

    return response


@router.get("/", response_model=list[WorkingHoursRead], status_code=status.HTTP_200_OK)
def list_working_hours(session: SessionDep) -> list[WorkingHoursRead]:
    today = utc_now().date()

    statement = (
        select(WorkingHours)
        .where(WorkingHours.date >= today)
        .order_by(WorkingHours.date)
    )

    working_hours = session.exec(statement).all()

    return [
        WorkingHoursRead.model_validate(working_hour) for working_hour in working_hours
    ]


@router.get(
    "/{working_hour_id}",
    response_model=WorkingHoursRead,
    status_code=status.HTTP_200_OK,
)
def read_working_hour(
    session: SessionDep,
    working_hour_id: int,
    user: User | None = Depends(get_current_user_optional),
) -> WorkingHoursRead:
    today = utc_now().date()

    query = select(WorkingHours).where(WorkingHours.id == working_hour_id)

    if not user or user.role != RoleEnum.ADMIN:
        query = query.where(WorkingHours.date >= today)

    working_hour = session.exec(query).first()

    if working_hour is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Fecha no encontrada"
        )

    response: WorkingHoursRead = WorkingHoursRead.model_validate(working_hour)

    return response
