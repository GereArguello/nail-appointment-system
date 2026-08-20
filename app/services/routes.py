from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app.auth.dependencies import get_current_admin, get_current_user_optional
from app.core.database import SessionDep
from app.core.enums import RoleEnum, StatusEnum
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


@router.get("/", response_model=list[ServiceRead], status_code=status.HTTP_200_OK)
def list_services(
    session: SessionDep,
    status: StatusEnum | None = None,
    current_user: User | None = Depends(get_current_user_optional),
) -> list[ServiceRead]:
    query = select(Service)

    if current_user and current_user.role == RoleEnum.ADMIN:
        if status:
            query = query.where(Service.status == status)
    else:
        query = query.where(Service.status == StatusEnum.ACTIVE)

    services = session.exec(query).all()

    return [ServiceRead.model_validate(service) for service in services]
