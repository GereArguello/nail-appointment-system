from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select

from app.appointments.helper import convert_business_range_to_utc
from app.appointments.models import Appointment
from app.appointments.schemas import AppointmentCreate, AppointmentRead
from app.appointments.service import (
    calculate_appointment_time_range,
    calculate_first_and_last_possible_start,
    get_appointment_or_404,
    get_appointments_by_date,
    get_business_settings_or_409,
    get_calendar_blocks_by_date,
    get_working_hour_by_date,
    has_appointment_overlap,
    has_calendar_block_overlap,
    resolve_appointment_payment_terms,
    validate_cancellation_deadline,
    validate_no_appointment_overlap,
    validate_no_calendar_block_overlap,
    validate_not_in_past,
    validate_within_working_hours,
)
from app.auth.dependencies import get_current_admin, get_current_user
from app.core.database import SessionDep
from app.core.date_ranges import date_range_as_datetime_utc, resolve_date_range
from app.core.datetime import as_utc, utc_now
from app.core.enums import AppointmentStatusEnum, RoleEnum
from app.services.service import get_service_or_404
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

    service = get_service_or_404(appointment_data.service_id, session)

    validate_not_in_past(appointment_data.starts_at, session)

    occupied_start, occupied_end = calculate_appointment_time_range(
        appointment_data.starts_at, service
    )

    try:
        validate_within_working_hours(occupied_start, occupied_end, session)

        occupied_start_utc, occupied_end_utc = convert_business_range_to_utc(
            session,
            occupied_start,
            occupied_end,
        )

        validate_no_calendar_block_overlap(
            occupied_start_utc, occupied_end_utc, session
        )

        validate_no_appointment_overlap(occupied_start_utc, occupied_end_utc, session)

        appointment_ends_local = appointment_data.starts_at + timedelta(
            minutes=service.duration_minutes
        )

        appointment_start_utc, appointment_end_utc = convert_business_range_to_utc(
            session,
            appointment_data.starts_at,
            appointment_ends_local,
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
            starts_at=appointment_start_utc,
            ends_at=appointment_end_utc,
            status=appointment_status,
            agreed_price=agreed_price,
            agreed_deposit=agreed_deposit,
            payment_expires_at=payment_expires_at,
            description=appointment_data.description,
        )

        session.add(appointment)
        session.commit()

    except Exception:
        session.rollback()
        raise

    session.refresh(appointment)

    appointment_read: AppointmentRead = AppointmentRead.model_validate(appointment)

    return appointment_read


@router.get("/availability")
def get_availability(
    target_date: date, service_id: int, session: SessionDep
) -> list[datetime]:
    """Obtiene los horarios disponibles para reservar un servicio en una fecha.

    Genera posibles inicios de cita según el intervalo de slots configurado en
    BusinessSettings, dentro del horario laboral disponible. Para cada candidato
    se considera la duración del servicio, sus buffers anterior y posterior,
    las tolerancias del negocio, los bloqueos de calendario y las citas existentes
    que ocupan disponibilidad.


    Devuelve únicamente las horas visibles de inicio de los turnos disponibles.

    Lanza 404 si la fecha no tiene horario laboral configurado o si el servicio
    no existe o no está disponible.

    Lanza 409 si el servicio no puede entrar dentro del rango laboral disponible."""
    working_hour = get_working_hour_by_date(session, target_date)
    calendar_blocks = get_calendar_blocks_by_date(session, target_date)
    appointments = get_appointments_by_date(session, target_date)
    service = get_service_or_404(service_id, session)
    business_settings = get_business_settings_or_409(session)

    first_possible_starts_at, last_possible_starts_at = (
        calculate_first_and_last_possible_start(
            working_hour, service, business_settings
        )
    )

    slots: list[datetime] = []

    appoint = first_possible_starts_at
    step = timedelta(minutes=business_settings.slot_interval_minutes)

    now_local = utc_now().astimezone(ZoneInfo(business_settings.timezone))

    is_today = target_date == now_local.date()

    while appoint <= last_possible_starts_at:
        if is_today and appoint <= now_local:
            appoint += step
            continue

        start_time, end_time = calculate_appointment_time_range(appoint, service)

        if not has_appointment_overlap(
            start_time, end_time, appointments
        ) and not has_calendar_block_overlap(start_time, end_time, calendar_blocks):
            slots.append(appoint.replace(tzinfo=None))

        appoint += step

    return slots


@router.get(
    "/{appointment_id}", response_model=AppointmentRead, status_code=status.HTTP_200_OK
)
def read_appointment(
    appointment_id: int,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> AppointmentRead:
    """Obtiene una cita por su identificador.

    Permite acceder a la cita al usuario propietario o a un
    administrador. Si la cita no existe o el usuario no tiene
    permiso para verla, devuelve un error 404.
    """
    appointment = get_appointment_or_404(appointment_id, session)

    if current_user.id != appointment.user_id and current_user.role != RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cita no encontrada",
        )

    response: AppointmentRead = AppointmentRead.model_validate(appointment)

    return response


@router.patch(
    "/{appointment_id}/confirm",
    response_model=AppointmentRead,
    status_code=status.HTTP_200_OK,
)
def confirm_appointment(
    appointment_id: int,
    session: SessionDep,
    current_user: User = Depends(get_current_admin),
) -> AppointmentRead:
    """Confirma una cita pendiente de confirmación.

    Solo los administradores pueden realizar esta acción.
    La cita debe encontrarse en estado PENDING_CONFIRMATION;
    cualquier otro estado genera un conflicto.
    """
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


@router.get("/", response_model=list[AppointmentRead], status_code=status.HTTP_200_OK)
def list_appointments(
    session: SessionDep,
    current_user: User = Depends(get_current_user),
    from_date: date | None = None,
    to_date: date | None = None,
) -> list[AppointmentRead]:
    """Lista las citas accesibles para el usuario autenticado.

    Los administradores pueden consultar todas las citas, mientras
    que los usuarios comunes solo pueden consultar las propias.

    Permite filtrar por un rango de fechas locales del negocio.
    El rango se convierte a UTC antes de realizar la consulta.
    """
    business_settings = get_business_settings_or_409(session)

    if current_user.role == RoleEnum.ADMIN:
        statement = select(Appointment)
    else:
        statement = select(Appointment).where(Appointment.user_id == current_user.id)

    start_date, end_date, _ = resolve_date_range(
        from_date=from_date,
        to_date=to_date,
        timezone=business_settings.timezone,
    )

    start_datetime, end_datetime = date_range_as_datetime_utc(
        start_date, end_date, timezone=business_settings.timezone
    )

    statement = statement.where(
        Appointment.starts_at >= start_datetime,
        Appointment.starts_at < end_datetime,
    )

    return list(session.exec(statement).all())


@router.patch(
    "/{appointment_id}/cancel",
    response_model=AppointmentRead,
    status_code=status.HTTP_200_OK,
)
def cancel_appointment(
    appointment_id: int,
    session: SessionDep,
    user: User = Depends(get_current_user),
) -> AppointmentRead:
    """Cancela una cita existente.

    El cliente solo puede cancelar sus propias citas y únicamente si se
    encuentran en un estado cancelable y dentro del plazo permitido.

    Los administradores pueden cancelar cualquier cita cancelable y no están
    sujetos al límite de tiempo de cancelación.
    """
    appointment = get_appointment_or_404(appointment_id, session)

    if appointment.user_id != user.id and user.role != RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cita no encontrada",
        )

    cancellable_statuses = {
        AppointmentStatusEnum.PENDING_CONFIRMATION,
        AppointmentStatusEnum.PENDING_PAYMENT,
        AppointmentStatusEnum.CONFIRMED,
    }

    if appointment.status not in cancellable_statuses:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La cita no puede ser cancelada en su estado actual",
        )

    validate_cancellation_deadline(session, appointment, user)

    appointment.status = (
        AppointmentStatusEnum.CANCELLED_BY_ADMIN
        if user.role == RoleEnum.ADMIN
        else AppointmentStatusEnum.CANCELLED_BY_CLIENT
    )

    session.commit()
    session.refresh(appointment)

    response: AppointmentRead = AppointmentRead.model_validate(appointment)

    return response


@router.patch(
    "/{appointment_id}/complete",
    response_model=AppointmentRead,
    status_code=status.HTTP_200_OK,
)
def complete_appointment(
    appointment_id: int, session: SessionDep, user: User = Depends(get_current_admin)
) -> AppointmentRead:
    """Marca una cita confirmada como completada.

    Solo los administradores pueden completar citas.
    La cita debe estar en estado confirmado y haber alcanzado
    su hora de finalización.
    """
    appointment = get_appointment_or_404(appointment_id, session)

    if appointment.status != AppointmentStatusEnum.CONFIRMED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La cita no puede ser completada en su estado actual",
        )

    if utc_now() < as_utc(appointment.ends_at):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La cita no puede completarse antes de su finalización",
        )

    appointment.status = AppointmentStatusEnum.COMPLETED

    session.commit()
    session.refresh(appointment)

    response: AppointmentRead = AppointmentRead.model_validate(appointment)

    return response
