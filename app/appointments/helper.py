from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlmodel import Session

from app.appointments.models import Appointment
from app.appointments.service import (
    calculate_appointment_time_range,
    calculate_first_and_last_possible_start,
    get_business_settings_or_409,
    has_appointment_overlap,
    has_calendar_block_overlap,
)
from app.business_settings.models import BusinessSettings
from app.calendar_blocks.models import CalendarBlock
from app.core.datetime import localize_business_datetime, utc_now
from app.services.models import Service
from app.working_hours.models import WorkingHour


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
