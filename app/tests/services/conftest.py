from collections.abc import Callable
from typing import Any, cast

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.enums import StatusEnum
from app.services.models import Service
from app.services.schemas import ServiceRead
from app.tests.factories import create_service_data
from app.users.schemas import UserRead


@pytest.fixture
def create_service(
    client: TestClient,
    admin_with_login: tuple[UserRead, str],
) -> Callable[..., ServiceRead]:
    _, token = admin_with_login

    def _create_service(**overrides: Any) -> ServiceRead:
        data = create_service_data(**overrides)

        response = client.post(
            "/services/",
            json=data,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_201_CREATED

        return cast(ServiceRead, ServiceRead.model_validate(response.json()))

    return _create_service


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
