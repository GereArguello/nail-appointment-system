from typing import cast

from fastapi import HTTPException, status

from app.core.database import SessionDep
from app.core.enums import StatusEnum
from app.services.models import Service


def get_service_or_404(
    service_id: int,
    session: SessionDep,
) -> Service:
    """Obtiene el servicio asociado a una cita.

    Lanza un error 404 si el servicio no existe o está inactivo.
    """
    service = session.get(Service, service_id)

    if not service or service.status == StatusEnum.INACTIVE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio no encontrado",
        )

    return cast(Service, service)
