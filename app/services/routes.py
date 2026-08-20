from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.auth.dependencies import get_current_admin
from app.core.database import SessionDep
from app.services.models import Service
from app.services.schemas import ServiceCreate, ServiceRead
from app.users.models import User

router = APIRouter(prefix="/services", tags=["services"])


@router.post(
    "/",
    response_model=ServiceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear servicio",
)
def create_service(
    service: ServiceCreate,
    session: SessionDep,
    current_admin: User = Depends(get_current_admin),
) -> ServiceRead:
    data = service.model_dump()
    db_service = Service(**data)

    try:
        session.add(db_service)
        session.commit()
        session.refresh(db_service)
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un servicio con ese nombre",
        ) from exc

    response: ServiceRead = ServiceRead.model_validate(db_service)

    return response
