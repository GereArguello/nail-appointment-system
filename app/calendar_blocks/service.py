from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.business_settings.service import get_business_now, get_business_settings_or_409
from app.calendar_blocks.models import CalendarBlock
from app.calendar_blocks.schemas import CalendarBlockCreate
from app.core.datetime import localize_business_datetime
from app.working_hours.models import WorkingHour


def get_overlapping_block(
    session: Session, data: CalendarBlockCreate
) -> CalendarBlock | None:
    """Busca un bloqueo existente que se superponga con el rango indicado."""
    business_settings = get_business_settings_or_409(session)

    starts_at_local = localize_business_datetime(
        data.starts_at, business_settings.timezone
    )

    ends_at_local = localize_business_datetime(data.ends_at, business_settings.timezone)

    starts_at_utc = starts_at_local.astimezone(UTC)
    ends_at_utc = ends_at_local.astimezone(UTC)

    query = select(CalendarBlock).where(
        CalendarBlock.starts_at < ends_at_utc,
        CalendarBlock.ends_at > starts_at_utc,
    )
    existing_block: CalendarBlock | None = session.exec(query).first()

    return existing_block


def validate_starts_at_not_in_past(
    session: Session,
    starts_at: datetime,
) -> None:
    """Valida que la fecha de inicio no sea anterior al momento actual.

    Interpreta la fecha recibida en la zona horaria configurada para el
    negocio y la compara con el momento actual en esa misma zona.

    Lanza 422 si la fecha de inicio está en el pasado.
    """
    business_settings = get_business_settings_or_409(session)

    starts_at_local = localize_business_datetime(
        starts_at,
        business_settings.timezone,
    )

    now = get_business_now(session)

    if starts_at_local < now:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="La fecha de inicio no puede ser anterior al momento actual",
        )


def validate_calendar_block_creation(
    session: Session,
    data: CalendarBlockCreate,
) -> None:
    """Valida las reglas necesarias para crear un bloqueo de calendario.

    El bloqueo no puede comenzar en el pasado, debe estar dentro de un
    horario laboral existente y no puede superponerse con otros bloqueos.
    """
    validate_starts_at_not_in_past(session, data.starts_at)

    working_hour = session.exec(
        select(WorkingHour).where(
            WorkingHour.date == data.starts_at.date(),
            WorkingHour.start_time <= data.starts_at.time(),
            WorkingHour.end_time >= data.ends_at.time(),
        )
    ).first()

    if working_hour is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede bloquear un horario si no es día laborable",
        )

    existing_block = get_overlapping_block(session, data)

    if existing_block:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El horario se superpone con otro bloqueo existente",
        )


def localize_calendar_block_range(
    session: Session, starts_at: datetime, ends_at: datetime
) -> tuple[datetime, datetime]:
    """Localiza el rango de un bloqueo según la zona horaria del negocio.

    Obtiene la configuración actual del negocio y aplica su zona horaria tanto
    al inicio como al final del bloqueo.

    Los datetimes naive se interpretan como horarios locales del negocio,
    mientras que los datetimes aware se convierten a dicha zona horaria.

    Devuelve una tupla con ambos datetimes localizados.
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

    return starts_at_local, ends_at_local
