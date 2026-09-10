from typing import cast

from sqlmodel import Session

from app.business_settings.models import BusinessSettings


def get_or_create_business_settings(
    session: Session,
) -> BusinessSettings:
    settings = session.get(BusinessSettings, 1)

    if settings is None:
        settings = BusinessSettings(id=1)

        session.add(settings)
        session.commit()
        session.refresh(settings)

    return cast(BusinessSettings, settings)
