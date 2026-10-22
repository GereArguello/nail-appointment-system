from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from threading import Event
from typing import Any

import pytest
from fastapi import Response
from sqlalchemy import Engine, text

import app.appointments.routes as appointment_routes
from app.business_settings.schemas import BusinessSettingsRead
from app.services.schemas import ServiceRead
from app.users.schemas import UserRead
from app.working_hours.schemas import WorkingHourRead


def test_concurrent_appointments(
    appointment_creation_setup: tuple[
        BusinessSettingsRead, ServiceRead, WorkingHourRead, datetime
    ],
    user_with_login: tuple[UserRead, str],
    post_appointment: Callable[..., Response],
    monkeypatch: pytest.MonkeyPatch,
    postgres_engine: Engine,
) -> None:
    _, service, _, starts_at = appointment_creation_setup
    _, token = user_with_login

    first_locked = Event()
    release_first = Event()
    second_entered = Event()
    second_passed = Event()

    original_validate = appointment_routes.validate_within_working_hours

    def reserve() -> Response:
        return post_appointment(
            service_id=service.id,
            starts_at=starts_at,
            token=token,
        )

    def controlled_validate(*args: Any, **kwargs: Any) -> None:
        # La primera solicitud adquiere el bloqueo.
        if not first_locked.is_set():
            original_validate(*args, **kwargs)

            first_locked.set()

            if not release_first.wait(timeout=10):
                raise TimeoutError("No se liberó la primera solicitud")
        else:
            # La segunda está por intentar adquirirlo.
            second_entered.set()

            original_validate(*args, **kwargs)

            # Solo llega acá si consiguió el bloqueo.
            second_passed.set()

    monkeypatch.setattr(
        appointment_routes,
        "validate_within_working_hours",
        controlled_validate,
    )

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(reserve)

        try:
            assert first_locked.wait(timeout=5)

            second = executor.submit(reserve)

            assert second_entered.wait(timeout=5)

            # La segunda solicitud no debería superar
            # la validación mientras A mantiene el bloqueo.
            assert not second_passed.wait(timeout=0.3)

            with postgres_engine.connect() as connection:
                result = connection.execute(
                    text("""
                        SELECT pid, wait_event_type, wait_event,
                            pg_blocking_pids(pid) AS blocked_by
                        FROM pg_stat_activity
                        WHERE wait_event_type = 'Lock'
                    """)
                ).all()

            assert any(
                wait_event_type == "Lock"
                and wait_event == "transactionid"
                and blocked_by
                for _, wait_event_type, wait_event, blocked_by in result
            )

        finally:
            # Liberar A incluso si falla una comprobación.
            release_first.set()

        responses = [first.result(), second.result()]

    status_codes = sorted(response.status_code for response in responses)

    assert status_codes == [201, 409]
