from datetime import date

from fastapi import HTTPException, status
from sqlmodel import Session

from app.business_settings.service import get_business_now


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
