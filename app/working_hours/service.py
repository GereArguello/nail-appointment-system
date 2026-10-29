from datetime import date

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.business_settings.service import get_business_now
from app.working_hours.models import WorkingHour


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


def get_working_hours_by_range(
    session: Session,
    start_date: date,
    end_date: date,
) -> list[WorkingHour]:
    """Obtiene los horarios laborales configurados dentro de un rango de fechas.

    Recupera los horarios laborales cuyas fechas se encuentran entre
    los límites del rango, incluyendo ambos extremos.

    Devuelve una lista de horarios laborales ordenados por fecha.
    """
    statement = (
        select(WorkingHour)
        .where(
            WorkingHour.date >= start_date,
            WorkingHour.date <= end_date,
        )
        .order_by(WorkingHour.date)
    )

    return list(session.exec(statement).all())
