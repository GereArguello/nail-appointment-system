from collections.abc import Callable

import pytest
from sqlmodel import Session

from app.core.enums import StatusEnum
from app.services.models import Service
from app.services.schemas import ServiceRead


@pytest.fixture
def inactive_service(
    session: Session, create_service: Callable[..., ServiceRead]
) -> ServiceRead:
    service = create_service(name="Manicura clásica 2")

    service_db = session.get(Service, service.id)

    assert service_db is not None

    service_db.status = StatusEnum.INACTIVE

    session.commit()
    session.refresh(service_db)

    inactive_service: ServiceRead = ServiceRead.model_validate(service_db)
    return inactive_service
