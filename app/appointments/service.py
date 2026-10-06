from datetime import UTC, date, datetime, timedelta
from typing import cast

from fastapi import HTTPException, status
from sqlmodel import col, select

from app.appointments.models import Appointment
from app.business_settings.service import get_business_settings_or_409
from app.calendar_blocks.models import CalendarBlock
from app.core.database import SessionDep
from app.core.date_ranges import date_range_as_datetime_utc
from app.core.datetime import as_utc, utc_now
from app.core.enums import AppointmentStatusEnum, RoleEnum
from app.services.models import Service
from app.users.models import User
from app.working_hours.models import WorkingHour


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
    starts_at: datetime,
    service: Service,
) -> tuple[datetime, datetime]:
    """Calcula el rango de tiempo realmente ocupado por una cita.

    Contempla la duración del servicio y los buffers configurados
    antes y después del inicio visible de la cita.
    """
    start_time = starts_at - timedelta(minutes=service.buffer_before_minutes)

    end_time = (
        starts_at
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
    business_settings = get_business_settings_or_409(session)

    day_start, day_end = date_range_as_datetime_utc(
        start_time.date(), end_time.date(), timezone=business_settings.timezone
    )

    blocking_statuses = {
        AppointmentStatusEnum.CONFIRMED,
        AppointmentStatusEnum.PENDING_CONFIRMATION,
        AppointmentStatusEnum.PENDING_PAYMENT,
    }

    query = (
        select(Appointment, Service)
        .join(Service, Appointment.service_id == Service.id)
        .where(
            Appointment.starts_at >= day_start,
            Appointment.ends_at <= day_end,
            col(Appointment.status).in_(blocking_statuses),
        )
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


def get_working_hour_by_date(
    session: SessionDep,
    target_date: date,
) -> WorkingHour:
    """Obtiene el horario laboral configurado para una fecha.

    Lanza 404 si la fecha no tiene un horario laboral definido.
    """
    working_hour = session.exec(
        select(WorkingHour).where(WorkingHour.date == target_date)
    ).first()

    if working_hour is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Esta fecha no tiene horario laborable",
        )

    return cast(WorkingHour, working_hour)


def get_calendar_blocks_by_date(
    session: SessionDep,
    target_date: date,
) -> list[CalendarBlock]:
    """Obtiene los bloqueos de calendario que intersectan una fecha.

    Incluye cualquier bloqueo que se superponga total o parcialmente
    con el rango correspondiente al día solicitado.
    """
    business_settings = get_business_settings_or_409(session)
    day_start, day_end = date_range_as_datetime_utc(
        target_date, target_date, timezone=business_settings.timezone
    )

    calendar_blocks = session.exec(
        select(CalendarBlock).where(
            CalendarBlock.starts_at < day_end,
            CalendarBlock.ends_at > day_start,
        )
    ).all()

    return list(calendar_blocks)


def get_appointments_by_date(
    session: SessionDep, target_date: date
) -> list[tuple[Appointment, Service]]:
    """Obtiene las citas que ocupan disponibilidad en una fecha.

    Devuelve cada cita junto con su servicio asociado para poder
    considerar los buffers del servicio al calcular superposiciones.

    Solo incluye citas en estados que reservan espacio en la agenda.
    """
    business_settings = get_business_settings_or_409(session)
    day_start, day_end = date_range_as_datetime_utc(
        target_date, target_date, timezone=business_settings.timezone
    )

    occupying_statuses = {
        AppointmentStatusEnum.CONFIRMED,
        AppointmentStatusEnum.PENDING_CONFIRMATION,
        AppointmentStatusEnum.PENDING_PAYMENT,
    }

    results = session.exec(
        select(Appointment, Service)
        .join(Service, Appointment.service_id == Service.id)
        .where(
            Appointment.starts_at < day_end,
            Appointment.ends_at > day_start,
            col(Appointment.status).in_(occupying_statuses),
        )
    ).all()

    return list(results)


def calculate_first_and_last_possible_start(
    session: SessionDep, working_hour: WorkingHour, service: Service
) -> tuple[datetime, datetime]:
    """Calcula el primer y último inicio posible para un servicio.

    Considera el horario laboral, las tolerancias configuradas del negocio,
    la duración del servicio y sus buffers anterior y posterior.

    Lanza 409 si el servicio no puede entrar dentro del rango disponible.
    """
    business_settings = get_business_settings_or_409(session)

    working_start = datetime.combine(
        working_hour.date,
        working_hour.start_time,
        tzinfo=UTC,
    )

    occupied_start_limit = working_start - timedelta(
        minutes=business_settings.appointment_start_tolerance_minutes
    )

    first_possible_starts_at = occupied_start_limit + timedelta(
        minutes=service.buffer_before_minutes
    )

    working_end = datetime.combine(
        working_hour.date,
        working_hour.end_time,
        tzinfo=UTC,
    )

    occupied_end_limit = working_end + timedelta(
        minutes=business_settings.appointment_end_tolerance_minutes
    )

    last_possible_starts_at = occupied_end_limit - timedelta(
        minutes=service.duration_minutes + service.buffer_after_minutes
    )

    if first_possible_starts_at > last_possible_starts_at:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El servicio no entra dentro del horario laboral disponible",
        )

    return first_possible_starts_at, last_possible_starts_at


def has_calendar_block_overlap(
    start_time: datetime,
    end_time: datetime,
    calendar_blocks: list[CalendarBlock],
) -> bool:
    """Indica si un rango se superpone con algún bloqueo de calendario."""
    start_time = as_utc(start_time)
    end_time = as_utc(end_time)

    return any(
        as_utc(block.starts_at) < end_time and as_utc(block.ends_at) > start_time
        for block in calendar_blocks
    )


def has_appointment_overlap(
    start_time: datetime,
    end_time: datetime,
    appointments: list[tuple[Appointment, Service]],
) -> bool:
    """Indica si un rango se superpone con alguna cita existente.

    La comparación considera los buffers del servicio asociado
    a cada cita existente.
    """
    for appointment, service in appointments:
        start_with_buffer = as_utc(
            appointment.starts_at - timedelta(minutes=service.buffer_before_minutes)
        )

        end_with_buffer = as_utc(
            appointment.ends_at + timedelta(minutes=service.buffer_after_minutes)
        )

        if (
            as_utc(start_time) < end_with_buffer
            and as_utc(end_time) > start_with_buffer
        ):
            return True

    return False
