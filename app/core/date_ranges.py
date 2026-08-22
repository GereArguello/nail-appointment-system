from datetime import UTC, date, datetime, time, timedelta

from fastapi import HTTPException, status

from app.core.enums import RoleEnum
from app.users.models import User
from app.utils import utc_now


def resolve_date_range(
    *,
    current_user: User | None,
    from_date: date | None,
    to_date: date | None,
) -> tuple[date, date]:
    today = utc_now().date()
    is_admin = current_user is not None and current_user.role == RoleEnum.ADMIN

    start_date = from_date or today
    end_date = to_date or start_date + timedelta(days=31)

    if start_date < today and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo administradores pueden ver fechas pasadas",
        )

    if end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La fecha final no puede ser anterior a la inicial",
        )

    if end_date - start_date > timedelta(days=31):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El rango no puede superar los 31 días",
        )

    return start_date, end_date


def date_range_as_datetime_utc(
    start_date: date,
    end_date: date,
) -> tuple[datetime, datetime]:
    start_datetime = datetime.combine(start_date, time.min, tzinfo=UTC)
    end_datetime = datetime.combine(end_date, time.max, tzinfo=UTC)

    return start_datetime, end_datetime
