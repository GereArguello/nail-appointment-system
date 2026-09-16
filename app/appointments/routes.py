from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status

from app.appointments.models import Appointment
from app.appointments.schemas import AppointmentCreate, AppointmentRead
from app.appointments.service import (
    calculate_appointment_time_range,
    get_appointment_or_404,
    get_service_or_404,
    resolve_appointment_payment_terms,
    validate_no_appointment_overlap,
    validate_no_calendar_block_overlap,
    validate_within_working_hours,
)
from app.auth.dependencies import get_current_admin, get_current_user
from app.core.database import SessionDep
from app.core.enums import AppointmentStatusEnum, RoleEnum
from app.users.models import User

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.post("/", response_model=AppointmentRead, status_code=status.HTTP_201_CREATED)
def create_appointment(
    appointment_data: AppointmentCreate,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> AppointmentRead:
    """Crea una nueva cita para el usuario autenticado.

    Valida la disponibilidad del horario solicitado, contemplando
    horarios laborales, bloqueos de calendario, citas existentes
    y buffers del servicio.

    Define la duración real de la cita, conserva el precio y la seña
    acordados al momento de reservar, calcula la expiración del
    pago cuando corresponde y asigna el estado inicial de la cita.
    """

    service = get_service_or_404(appointment_data, session)

    start_time, end_time = calculate_appointment_time_range(appointment_data, service)

    validate_within_working_hours(start_time, end_time, session)

    validate_no_calendar_block_overlap(start_time, end_time, session)

    validate_no_appointment_overlap(start_time, end_time, session)

    appointment_ends_at = appointment_data.starts_at + timedelta(
        minutes=service.duration_minutes
    )

    agreed_price, agreed_deposit, payment_expires_at = (
        resolve_appointment_payment_terms(service, session)
    )

    appointment_status = (
        AppointmentStatusEnum.PENDING_CONFIRMATION
        if payment_expires_at is None
        else AppointmentStatusEnum.PENDING_PAYMENT
    )

    appointment = Appointment(
        user_id=current_user.id,
        service_id=appointment_data.service_id,
        starts_at=appointment_data.starts_at,
        ends_at=appointment_ends_at,
        status=appointment_status,
        agreed_price=agreed_price,
        agreed_deposit=agreed_deposit,
        payment_expires_at=payment_expires_at,
        description=appointment_data.description,
    )

    session.add(appointment)
    session.commit()
    session.refresh(appointment)

    appointment_read: AppointmentRead = AppointmentRead.model_validate(appointment)

    return appointment_read


@router.get(
    "/{appointment_id}", response_model=AppointmentRead, status_code=status.HTTP_200_OK
)
def read_appointment(
    appointment_id: int, session: SessionDep, user: User = Depends(get_current_user)
) -> AppointmentRead:
    appointment = get_appointment_or_404(appointment_id, session)

    if user.id != appointment.user_id and user.role != RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Turno no encontrado",
        )

    response: AppointmentRead = AppointmentRead.model_validate(appointment)

    return response


@router.patch(
    "/{appointment_id}/confirm",
    response_model=AppointmentRead,
    status_code=status.HTTP_200_OK,
)
def confirm_appointment(
    appointment_id: int, session: SessionDep, user: User = Depends(get_current_admin)
) -> AppointmentRead:
    appointment = get_appointment_or_404(appointment_id, session)

    if appointment.status != AppointmentStatusEnum.PENDING_CONFIRMATION:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La cita no puede ser confirmada en su estado actual",
        )

    appointment.status = AppointmentStatusEnum.CONFIRMED

    session.commit()
    session.refresh(appointment)

    response: AppointmentRead = AppointmentRead.model_validate(appointment)

    return response
