from datetime import UTC, datetime

from sqlmodel import Session

from app.business_settings.service import get_business_settings_or_409
from app.core.datetime import localize_business_datetime


def convert_business_range_to_utc(
    session: Session,
    starts_at: datetime,
    ends_at: datetime,
) -> tuple[datetime, datetime]:
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
