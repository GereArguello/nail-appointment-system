from fastapi import APIRouter, Depends, status

from app.auth.dependencies import get_current_admin
from app.business_settings.schemas import BusinessSettingsRead, BusinessSettingsUpdate
from app.business_settings.service import get_or_create_business_settings
from app.core.database import SessionDep
from app.users.models import User

router = APIRouter(
    prefix="/business-settings",
    tags=["business-settings"],
)


@router.get("/", response_model=BusinessSettingsRead, status_code=status.HTTP_200_OK)
def read_business_settings(
    session: SessionDep,
    current_user: User = Depends(get_current_admin),
) -> BusinessSettingsRead:
    """Obtiene la configuración actual del negocio.

    Si la configuración aún no existe, crea una utilizando los valores predeterminados.
    Requiere permisos de administrador.
    """
    return get_or_create_business_settings(session)


@router.patch("/", response_model=BusinessSettingsRead, status_code=status.HTTP_200_OK)
def update_business_settings(
    session: SessionDep,
    data: BusinessSettingsUpdate,
    user: User = Depends(get_current_admin),
) -> BusinessSettingsRead:
    """Actualiza parcialmente la configuración del negocio.

    Modifica únicamente los campos proporcionados en la solicitud.
    Si la configuración aún no existe, la crea con los valores predeterminados antes de
    aplicar los cambios. Requiere permisos de administrador.
    """
    business_settings = get_or_create_business_settings(session)

    update_data = data.model_dump(exclude_unset=True)

    business_settings.sqlmodel_update(update_data)

    session.commit()
    session.refresh(business_settings)

    return business_settings
