from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlmodel import Session

from app.appointments.models import Appointment
from app.business_settings.models import BusinessSettings
from app.business_settings.schemas import BusinessSettingsRead
from app.business_settings.service import get_business_settings_or_409
from app.calendar_blocks.models import CalendarBlock
from app.core.datetime import as_utc, localize_business_datetime, utc_now
from app.services.models import Service
from app.working_hours.models import WorkingHour


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


def calculate_first_and_last_possible_start(
    working_hour: WorkingHour, service: Service, business_settings: BusinessSettingsRead
) -> tuple[datetime, datetime]:
    """Calcula el primer y último inicio posible para un servicio.

    Considera el horario laboral, las tolerancias configuradas del negocio,
    la duración del servicio y sus buffers anterior y posterior.

    Lanza 409 si el servicio no puede entrar dentro del rango disponible.
    """
    timezone = ZoneInfo(business_settings.timezone)

    working_start = datetime.combine(
        working_hour.date,
        working_hour.start_time,
        tzinfo=timezone,
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
        tzinfo=timezone,
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
    start_time_utc = start_time.astimezone(UTC)
    end_time_utc = end_time.astimezone(UTC)

    return any(
        as_utc(block.starts_at) < end_time_utc
        and as_utc(block.ends_at) > start_time_utc
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
    start_time_utc = start_time.astimezone(UTC)
    end_time_utc = end_time.astimezone(UTC)

    for appointment, service in appointments:
        start_with_buffer = as_utc(
            appointment.starts_at - timedelta(minutes=service.buffer_before_minutes)
        )

        end_with_buffer = as_utc(
            appointment.ends_at + timedelta(minutes=service.buffer_after_minutes)
        )

        if start_time_utc < end_with_buffer and end_time_utc > start_with_buffer:
            return True

    return False


def convert_business_range_to_utc(
    session: Session,
    starts_at: datetime,
    ends_at: datetime,
) -> tuple[datetime, datetime]:
    """Convierte un rango de fechas y horas locales del negocio a UTC.

    Interpreta ambos extremos según la zona horaria configurada
    del negocio y los convierte a datetimes con zona horaria UTC.

    Devuelve una tupla con el inicio y el fin del rango en UTC.

    Lanza 409 si no se puede obtener la configuración del negocio.
    """
    business_settings = get_business_settings_or_409(session)

    starts_at_utc = localize_business_datetime(
        starts_at,
        business_settings.timezone,
    ).astimezone(UTC)

    ends_at_utc = localize_business_datetime(
        ends_at,
        business_settings.timezone,
    ).astimezone(UTC)

    return starts_at_utc, ends_at_utc


def iter_available_slots(
    working_hour: WorkingHour,
    service: Service,
    business_settings: BusinessSettings,
    appointments: list[tuple[Appointment, Service]],
    calendar_blocks: list[CalendarBlock],
    target_date: date,
) -> Iterator[datetime]:
    """Genera los horarios disponibles para reservar un servicio en una fecha.

    Calcula los posibles inicios de cita según el horario laboral, la duración
    del servicio, sus buffers, las tolerancias del negocio y el intervalo
    de slots configurado.

    Descarta los horarios que se superponen con citas existentes o bloqueos
    de calendario, así como los horarios pasados si la fecha es el día actual.

    Produce mediante un generador los inicios disponibles como datetimes
    locales sin información de zona horaria, permitiendo consumirlos
    individualmente sin calcular necesariamente todos los horarios.

    Lanza 409 si el servicio no entra dentro del horario laboral disponible.
    """
    first, last = calculate_first_and_last_possible_start(
        working_hour, service, business_settings
    )

    appoint = first
    step = timedelta(minutes=business_settings.slot_interval_minutes)

    now_local = utc_now().astimezone(ZoneInfo(business_settings.timezone))

    is_today = target_date == now_local.date()

    while appoint <= last:
        if is_today and appoint <= now_local:
            appoint += step
            continue

        start_time, end_time = calculate_appointment_time_range(appoint, service)

        if not has_appointment_overlap(
            start_time, end_time, appointments
        ) and not has_calendar_block_overlap(start_time, end_time, calendar_blocks):
            yield appoint.replace(tzinfo=None)

        appoint += step
