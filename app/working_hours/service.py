from datetime import date, datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlmodel import Session

from app.business_settings.service import get_business_settings_or_409
from app.core.enums import TimezoneEnum
from app.utils import utc_now


def validate_working_hour_date(
    session: Session,
    target_date: date,
) -> None:
    """Valida que la fecha laboral no sea anterior al día actual del negocio.

    Obtiene la fecha actual según la zona horaria configurada para
    el negocio y la compara con la fecha proporcionada.

    Lanza 422 si la fecha pertenece a un día anterior.
    """
    business_today = get_business_now(session).date()

    if target_date < business_today:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="La fecha no puede ser anterior a hoy",
        )


def get_now_in_timezone(timezone: TimezoneEnum) -> datetime:
    """Obtiene el instante actual expresado en la zona horaria indicada.

    Convierte la hora actual UTC a la zona horaria proporcionada,
    conservando el mismo instante absoluto.
    """
    return utc_now().astimezone(ZoneInfo(timezone))


def get_today_in_timezone(timezone: TimezoneEnum) -> date:
    """Obtiene la fecha actual según la zona horaria indicada.

    Devuelve únicamente la fecha local, sin información horaria.
    """
    return get_now_in_timezone(timezone).date()


def get_business_now(session: Session) -> datetime:
    """Obtiene la fecha y hora actuales en la zona horaria del negocio.

    Recupera la configuración almacenada y utiliza su zona horaria
    para expresar el instante actual.

    Propaga el error 409 si la configuración del negocio no existe.
    """
    business_settings = get_business_settings_or_409(session)
    return get_now_in_timezone(business_settings.timezone)
