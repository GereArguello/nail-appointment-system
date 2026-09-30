from typing import cast

from fastapi import HTTPException, status
from sqlmodel import Session

from app.business_settings.models import BusinessSettings
from app.core.config import settings


def get_or_create_business_settings(
    session: Session,
) -> BusinessSettings:
    """Obtiene la configuración del negocio o crea una por defecto.

    Busca la configuración única del negocio con ID 1.
    Si aún no existe, la crea utilizando la configuración inicial
    del entorno y los valores predeterminados del modelo.
    """
    business_settings = session.get(BusinessSettings, 1)

    if business_settings is None:
        business_settings = BusinessSettings(id=1, timezone=settings.BUSINESS_TIMEZONE)

        session.add(business_settings)
        session.commit()
        session.refresh(business_settings)

    return cast(BusinessSettings, business_settings)


def get_business_settings_or_409(
    session: Session,
) -> BusinessSettings:
    """Obtiene la configuración del negocio almacenada en la base de datos.

    Busca el registro único de configuración del negocio con ID 1.

    Devuelve la configuración encontrada o lanza 409 si el negocio
    todavía no está configurado para recibir citas.
    """
    business_settings = session.get(BusinessSettings, 1)

    if business_settings is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El negocio aún no está configurado para recibir citas",
        )

    return cast(BusinessSettings, business_settings)
