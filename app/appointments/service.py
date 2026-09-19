from datetime import datetime, timedelta
from typing import cast

from fastapi import HTTPException, status
from sqlmodel import select

from app.appointments.models import Appointment
from app.appointments.schemas import AppointmentCreate
from app.business_settings.models import BusinessSettings
from app.calendar_blocks.models import CalendarBlock
from app.core.database import SessionDep
from app.core.date_ranges import date_range_as_datetime_utc
from app.core.enums import AppointmentStatusEnum, RoleEnum
from app.services.models import Service
from app.users.models import User
from app.utils import as_utc, utc_now
from app.working_hours.models import WorkingHour


def get_service_or_404(appointment: AppointmentCreate, session: SessionDep) -> Service:
    """Obtiene el servicio asociado a una cita.

    Lanza un error 404 si el servicio solicitado no existe.
    """
    service = session.get(Service, appointment.service_id)

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Servicio no encontrado"
        )

    return cast(Service, service)


def get_business_settings_or_409(
    session: SessionDep,
) -> BusinessSettings:
    """Obtiene la configuración actual del negocio.
    Lanza un error 409 si el negocio aún no fue configurado
    para recibir citas.
    """
    business_settings = session.exec(select(BusinessSettings)).first()

    if business_settings is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El negocio aún no está configurado para recibir citas",
        )

    return cast(BusinessSettings, business_settings)


def get_appointment_or_404(appointment_id: int, session: SessionDep) -> Appointment:
    """Obtiene la cita asociada por id.

    Lanza un error 404 si la cita solicitada no existe.
    """
    appointment = session.get(Appointment, appointment_id)

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cita no encontrada"
        )

    return cast(Appointment, appointment)


def calculate_appointment_time_range(
    appointment: AppointmentCreate, service: Service
) -> tuple[datetime, datetime]:
    """Calcula el rango de tiempo ocupado por una cita.

    Contempla la duración del servicio y los buffers configurados
    antes y después del mismo."""
    start_time = appointment.starts_at - timedelta(
        minutes=service.buffer_before_minutes
    )

    end_time = (
        appointment.starts_at
        + timedelta(minutes=service.duration_minutes)
        + timedelta(minutes=service.buffer_after_minutes)
    )

    return start_time, end_time


def validate_within_working_hours(
    start_time: datetime, end_time: datetime, session: SessionDep
) -> None:
    """Valida que una cita se encuentre dentro del horario laboral.

    El rango ocupado debe estar contenido en un horario laboral existente,
    contemplando las tolerancias de inicio y finalización configuradas
    para el negocio.
    """
    business_settings = get_business_settings_or_409(session)

    adjusted_start_time = (
        start_time
        + timedelta(minutes=business_settings.appointment_start_tolerance_minutes)
    ).time()

    adjusted_end_time = (
        end_time
        - timedelta(minutes=business_settings.appointment_end_tolerance_minutes)
    ).time()

    query = select(WorkingHour).where(
        (WorkingHour.date == start_time.date())
        & (WorkingHour.start_time <= adjusted_start_time)
        & (WorkingHour.end_time >= adjusted_end_time)
    )

    working_hour = session.exec(query).first()

    if working_hour is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La cita solicitada está fuera del horario disponible",
        )


def validate_no_calendar_block_overlap(
    start_time: datetime, end_time: datetime, session: SessionDep
) -> None:
    """Valida que una cita no se superponga con un bloqueo de calendario.

    El rango ocupado por la cita no puede coincidir total ni parcialmente
    con un bloqueo existente."""
    query = select(CalendarBlock).where(
        (CalendarBlock.starts_at < end_time) & (CalendarBlock.ends_at > start_time)
    )

    calendar_block = session.exec(query).first()

    if calendar_block:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Horario bloqueado por el administrador",
        )


def validate_no_appointment_overlap(
    start_time: datetime, end_time: datetime, session: SessionDep
) -> None:
    """Valida que una cita no se superponga con otra cita existente.

    La comparación contempla los buffers configurados en el servicio
    asociado a cada cita existente."""
    day_start, day_end = date_range_as_datetime_utc(start_time.date(), end_time.date())

    query = (
        select(Appointment, Service)
        .join(Service, Appointment.service_id == Service.id)
        .where((Appointment.starts_at >= day_start) & (Appointment.ends_at <= day_end))
    )

    results = session.exec(query).all()

    for appointment, service in results:
        start_with_buffer = appointment.starts_at - timedelta(
            minutes=service.buffer_before_minutes
        )
        end_with_buffer = appointment.ends_at + timedelta(
            minutes=service.buffer_after_minutes
        )

        if start_time < end_with_buffer and end_time > start_with_buffer:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Horario ya ocupado"
            )


def resolve_appointment_payment_terms(
    service: Service, session: SessionDep
) -> tuple[int, int, datetime | None]:
    """Resuelve las condiciones de pago de una cita.

    Toma el precio y la seña configurados en el servicio y,
    cuando corresponde una seña, calcula la fecha de expiración del pago
    según la configuración del negocio.
    """
    agreed_price = service.price
    agreed_deposit = service.deposit_amount
    payment_expires_at: datetime | None = None

    if agreed_deposit > 0:
        business_settings = get_business_settings_or_409(session)
        payment_expires_at = utc_now() + timedelta(
            hours=business_settings.deposit_payment_expiration_hours
        )

    return agreed_price, agreed_deposit, payment_expires_at


def validate_cancellation_deadline(
    session: SessionDep,
    appointment: Appointment,
    user: User,
) -> None:
    """Valida que una cita confirmada aún pueda ser cancelada.

    Los administradores no están sujetos al límite de cancelación.
    Para usuarios comunes, el límite se calcula según la configuración
    del negocio.
    """
    business_settings = get_business_settings_or_409(session)

    starts_at = as_utc(appointment.starts_at)

    cancellation_deadline = starts_at - timedelta(
        hours=business_settings.appointment_cancellation_limit_hours
    )

    if (
        user.role != RoleEnum.ADMIN
        and appointment.status == AppointmentStatusEnum.CONFIRMED
        and utc_now() > cancellation_deadline
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La cita ya no se puede cancelar",
        )
