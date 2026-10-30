from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import cast
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlmodel import Session, col, select

from app.appointments.helper import iter_available_slots
from app.appointments.models import Appointment
from app.appointments.schemas import CalendarAvailabilityRead
from app.business_settings.models import BusinessSettings
from app.business_settings.service import get_business_now, get_business_settings_or_409
from app.calendar_blocks.models import CalendarBlock
from app.calendar_blocks.service import get_calendar_blocks_by_range
from app.core.date_ranges import date_range_as_datetime_utc
from app.core.datetime import as_utc, localize_business_datetime, utc_now
from app.core.enums import AppointmentStatusEnum, RoleEnum
from app.services.models import Service
from app.services.service import get_service_or_404
from app.users.models import User
from app.working_hours.models import WorkingHour
from app.working_hours.service import get_working_hours_by_range


def get_appointment_or_404(appointment_id: int, session: Session) -> Appointment:
    """Obtiene la cita asociada por id.

    Lanza un error 404 si la cita solicitada no existe.
    """
    appointment = session.get(Appointment, appointment_id)

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cita no encontrada"
        )

    return cast(Appointment, appointment)


def validate_not_in_past(
    starts_at: datetime,
    session: Session,
) -> None:
    """Valida que el inicio de una cita no haya ocurrido.

    Interpreta starts_at en la zona horaria del negocio y lo compara
    con el instante actual en UTC.

    Lanza 422 si la fecha y hora de inicio no son futuras.
    """
    business_settings = get_business_settings_or_409(session)

    starts_at_utc = localize_business_datetime(
        starts_at,
        business_settings.timezone,
    ).astimezone(UTC)

    if starts_at_utc <= utc_now():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="La fecha de la cita no puede estar en el pasado",
        )


def validate_within_working_hours(
    start_time: datetime, end_time: datetime, session: Session
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

    query = (
        select(WorkingHour)
        .where(WorkingHour.date == start_time.date())
        .with_for_update()
    )

    working_hour = session.exec(query).first()

    if working_hour is None:
        raise HTTPException(
            status_code=404,
            detail="No existe horario laboral para ese día",
        )

    if not (
        working_hour.start_time <= adjusted_start_time
        and working_hour.end_time >= adjusted_end_time
    ):
        raise HTTPException(
            status_code=409,
            detail="La cita solicitada está fuera del horario disponible",
        )


def validate_no_calendar_block_overlap(
    start_time_utc: datetime,
    end_time_utc: datetime,
    session: Session,
) -> None:
    """Valida que una cita no se superponga con un bloqueo de calendario."""

    query = select(CalendarBlock).where(
        (CalendarBlock.starts_at < end_time_utc)
        & (CalendarBlock.ends_at > start_time_utc)
    )

    calendar_block = session.exec(query).first()

    if calendar_block:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Horario bloqueado por el administrador",
        )


def validate_no_appointment_overlap(
    start_time_utc: datetime,
    end_time_utc: datetime,
    session: Session,
) -> None:
    """Valida que una cita no se superponga con otra cita existente.

    La comparación contempla los buffers configurados en el servicio
    asociado a cada cita existente.
    """
    business_settings = get_business_settings_or_409(session)

    day_start, day_end = date_range_as_datetime_utc(
        start_time_utc.astimezone(ZoneInfo(business_settings.timezone)).date(),
        end_time_utc.astimezone(ZoneInfo(business_settings.timezone)).date(),
        timezone=business_settings.timezone,
    )

    blocking_statuses = {
        AppointmentStatusEnum.CONFIRMED,
        AppointmentStatusEnum.PENDING_CONFIRMATION,
        AppointmentStatusEnum.PENDING_PAYMENT,
        AppointmentStatusEnum.COMPLETED,
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
        appointment_starts_at = as_utc(appointment.starts_at)
        appointment_ends_at = as_utc(appointment.ends_at)

        start_with_buffer = appointment_starts_at - timedelta(
            minutes=service.buffer_before_minutes
        )
        end_with_buffer = appointment_ends_at + timedelta(
            minutes=service.buffer_after_minutes
        )

        if start_time_utc < end_with_buffer and end_time_utc > start_with_buffer:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Horario ya ocupado",
            )


def localize_appointment_range_to_utc(
    session: Session,
    starts_at: datetime,
    ends_at: datetime,
) -> tuple[datetime, datetime]:
    """Convierte un rango de cita desde la zona del negocio a UTC.

    Los datetimes naive se interpretan como horarios locales del negocio.
    Los datetimes aware se convierten preservando el instante que representan.

    Devuelve el inicio y fin del rango como datetimes aware en UTC.
    """
    business_settings = get_business_settings_or_409(session)

    starts_at_local = localize_business_datetime(
        starts_at,
        business_settings.timezone,
    )

    ends_at_local = localize_business_datetime(
        ends_at,
        business_settings.timezone,
    )

    return (
        starts_at_local.astimezone(UTC),
        ends_at_local.astimezone(UTC),
    )


def resolve_appointment_payment_terms(
    service: Service, session: Session
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
    session: Session,
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
    session: Session,
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
    session: Session,
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
    session: Session, target_date: date
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
        AppointmentStatusEnum.COMPLETED,
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


def get_appointments_by_range(
    session: Session,
    start_date: date,
    end_date: date,
    business_settings: BusinessSettings,
    user_id: int | None = None,
) -> list[Appointment]:
    """Obtiene las citas cuyo inicio pertenece a un rango de fechas.

    Convierte los límites del rango a UTC según la zona horaria del negocio
    y recupera las citas que comienzan dentro de él.

    Permite filtrar por usuario cuando se proporciona su identificador.
    Si no se especifica, recupera las citas de todos los usuarios,
    independientemente de su estado.

    Devuelve una lista de citas ordenadas por fecha y hora de inicio.
    """
    start_datetime, end_datetime = date_range_as_datetime_utc(
        start_date,
        end_date,
        timezone=business_settings.timezone,
    )

    statement = select(Appointment).where(
        Appointment.starts_at >= start_datetime,
        Appointment.starts_at < end_datetime,
    )

    if user_id is not None:
        statement = statement.where(Appointment.user_id == user_id)

    statement = statement.order_by(Appointment.starts_at)

    return list(session.exec(statement).all())


def get_occupying_appointments_by_range(
    session: Session,
    start_date: date,
    end_date: date,
    business_settings: BusinessSettings,
) -> list[tuple[Appointment, Service]]:
    """Obtiene las citas que ocupan disponibilidad en un rango de fechas.

    Convierte los límites del rango a UTC según la zona horaria del negocio
    y recupera las citas cuyos intervalos se superponen con él.

    Considera únicamente las citas confirmadas, pendientes de confirmación
    o pendientes de pago, excluyendo los estados que no ocupan disponibilidad.

    Devuelve una lista de tuplas con cada cita y su servicio asociado,
    ordenadas por fecha y hora de inicio.
    """
    start_datetime, end_datetime = date_range_as_datetime_utc(
        start_date,
        end_date,
        timezone=business_settings.timezone,
    )

    OCCUPYING_STATUSES = (
        AppointmentStatusEnum.CONFIRMED,
        AppointmentStatusEnum.PENDING_CONFIRMATION,
        AppointmentStatusEnum.PENDING_PAYMENT,
        AppointmentStatusEnum.COMPLETED,
    )

    statement = (
        select(Appointment, Service)
        .join(Service, Appointment.service_id == Service.id)
        .where(
            Appointment.starts_at < end_datetime,
            Appointment.ends_at > start_datetime,
            col(Appointment.status).in_(OCCUPYING_STATUSES),
        )
        .order_by(Appointment.starts_at)
    )

    return list(session.exec(statement).all())


def validate_calendar_availability_range(
    session: Session,
    from_date: date,
    to_date: date,
) -> None:
    """Valida el rango de fechas solicitado para consultar disponibilidad.

    Comprueba que la fecha inicial no sea anterior al día actual del negocio,
    que la fecha final no preceda a la inicial y que el rango no supere
    los 31 días inclusive.

    Utiliza la zona horaria configurada del negocio para determinar
    la fecha actual.

    Lanza 422 si alguna de las condiciones no se cumple.
    """
    business_now = get_business_now(session)
    today = business_now.date()

    if from_date < today:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="La fecha inicial no puede estar en el pasado",
        )

    if to_date < from_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="La fecha final no puede ser anterior a la inicial",
        )

    if (to_date - from_date).days > 30:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="El rango no puede superar los 31 días",
        )


def calculate_calendar_availability(
    session: Session,
    service_id: int,
    from_date: date,
    to_date: date,
) -> list[CalendarAvailabilityRead]:
    """Calcula la disponibilidad diaria de un servicio en un rango de fechas.

    Obtiene los horarios laborales, bloqueos de calendario y citas que
    ocupan disponibilidad mediante consultas por rango, agrupándolos
    por fecha según la zona horaria del negocio.

    Para cada día, comprueba si existe al menos un horario válido
    para el servicio solicitado, considerando su duración, buffers,
    tolerancias, bloqueos y citas existentes.

    Devuelve una lista ordenada de fechas con un booleano que indica
    si existe disponibilidad. Los días sin horario laboral o en los
    que el servicio no entra en la jornada se consideran no disponibles.

    Lanza 404 si el servicio no existe o no está disponible.
    Lanza 409 si no se puede obtener la configuración del negocio.
    """
    service = get_service_or_404(service_id, session)
    business_settings = get_business_settings_or_409(session)

    working_hours = get_working_hours_by_range(session, from_date, to_date)

    working_hours_by_date = {wh.date: wh for wh in working_hours}

    calendar_blocks = get_calendar_blocks_by_range(
        session,
        from_date,
        to_date,
        business_settings,
    )

    calendar_blocks_by_date = defaultdict(list)
    business_tz = ZoneInfo(business_settings.timezone)

    for cb in calendar_blocks:
        local_date = cb.starts_at.astimezone(business_tz).date()
        calendar_blocks_by_date[local_date].append(cb)

    appointments = get_occupying_appointments_by_range(
        session,
        from_date,
        to_date,
        business_settings,
    )

    appointments_by_date = defaultdict(list)

    for appointment, appointment_service in appointments:
        local_date = appointment.starts_at.astimezone(business_tz).date()
        appointments_by_date[local_date].append((appointment, appointment_service))

    current_date = from_date
    results = []

    while current_date <= to_date:
        working_hour = working_hours_by_date.get(current_date)

        if working_hour is None:
            results.append(
                CalendarAvailabilityRead(
                    date=current_date,
                    available=False,
                )
            )
            current_date += timedelta(days=1)
            continue

        daily_appointments = appointments_by_date[current_date]
        daily_blocks = calendar_blocks_by_date[current_date]

        try:
            available = (
                next(
                    iter_available_slots(
                        working_hour,
                        service,
                        business_settings,
                        daily_appointments,
                        daily_blocks,
                        current_date,
                    ),
                    None,
                )
                is not None
            )

        except HTTPException as exc:
            if (
                exc.status_code != status.HTTP_409_CONFLICT
                or exc.detail
                != "El servicio no entra dentro del horario laboral disponible"
            ):
                raise

            available = False

        results.append(CalendarAvailabilityRead(date=current_date, available=available))

        current_date += timedelta(days=1)

    return results
