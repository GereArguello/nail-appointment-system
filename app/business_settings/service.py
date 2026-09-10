from typing import cast

from sqlmodel import Session

from app.business_settings.models import BusinessSettings


def get_or_create_business_settings(
    session: Session,
) -> BusinessSettings:
    """Obtiene la configuración del negocio o crea una por defecto.

    Busca la configuración única del negocio con ID 1.
    Si aún no existe, la crea utilizando los valores predeterminados del modelo.
    """
    settings = session.get(BusinessSettings, 1)

    if settings is None:
        settings = BusinessSettings(id=1)

        session.add(settings)
        session.commit()
        session.refresh(settings)

    return cast(BusinessSettings, settings)
