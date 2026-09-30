from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.core.config import settings
from app.core.enums import TimezoneEnum


def get_local_date(
    days_offset: int = 0,
    timezone: TimezoneEnum | None = None,
) -> str:
    """Obtiene una fecha relativa al día actual en la zona horaria indicada.

    Utiliza la zona horaria configurada para el negocio si no se proporciona
    ninguna. Permite obtener fechas pasadas o futuras mediante days_offset.

    Devuelve la fecha como cadena en formato ISO 8601 (YYYY-MM-DD).
    """
    tz = ZoneInfo((timezone or settings.BUSINESS_TIMEZONE).value)

    return (datetime.now(tz) + timedelta(days=days_offset)).date().isoformat()
