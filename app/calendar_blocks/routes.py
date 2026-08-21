from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import get_current_admin
from app.calendar_blocks.models import CalendarBlock
from app.calendar_blocks.schemas import CalendarBlockCreate, CalendarBlockRead
from app.calendar_blocks.service import get_overlapping_block
from app.core.database import SessionDep
from app.users.models import User

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
