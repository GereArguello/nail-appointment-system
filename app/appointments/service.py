from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlmodel import select

from app.appointments.models import Appointment
from app.appointments.schemas import AppointmentCreate
from app.business_settings.models import BusinessSettings
from app.calendar_blocks.models import CalendarBlock
from app.core.database import SessionDep
from app.core.date_ranges import date_range_as_datetime_utc
from app.services.models import Service
from app.working_hours.models import WorkingHour


def calculate_appointment_time_range(
    appointment: AppointmentCreate, session: SessionDep
) -> tuple[datetime, datetime]:
    """Calcula el rango de tiempo ocupado por una cita.

    Contempla la duración del servicio y los buffers configurados
    antes y después del mismo."""
    service = session.get(Service, appointment.service_id)

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Servicio no encontrado"
        )

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
    contemplando la tolerancia de finalización configurada para el negocio."""
    business_settings = session.exec(select(BusinessSettings)).first()

    if business_settings is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="La configuración del negocio no está disponible",
        )

    tolerance_minutes = business_settings.appointment_end_tolerance_minutes

    end_time_with_tolerance = (end_time - timedelta(minutes=tolerance_minutes)).time()

    query = select(WorkingHour).where(
        (WorkingHour.date == start_time.date())
        & (WorkingHour.start_time <= start_time.time())
        & (WorkingHour.end_time >= end_time_with_tolerance)
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
            status_code=status.HTTP_409_CONFLICT, detail="Horario no disponible"
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
