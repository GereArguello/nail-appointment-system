from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.auth.dependencies import get_current_admin
from app.core.database import SessionDep
from app.users.models import User
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
