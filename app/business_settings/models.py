from datetime import datetime

from sqlmodel import Field, SQLModel

from app.core.datetime import utc_now
from app.core.enums import TimezoneEnum


class BusinessSettingsBase(SQLModel):
    timezone: TimezoneEnum

    appointment_start_tolerance_minutes: int = Field(default=10, ge=0)
    appointment_end_tolerance_minutes: int = Field(default=10, ge=0)
    appointment_cancellation_limit_hours: int = Field(default=8, ge=0)

    slot_interval_minutes: int = Field(
        default=15,
        ge=10,
        le=60,
        multiple_of=5,
    )

    deposit_payment_expiration_hours: int = Field(default=24, ge=1, le=168)


class BusinessSettings(BusinessSettingsBase, table=True):  # type: ignore[call-arg]
    id: int | None = Field(default=None, primary_key=True)

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(
        default_factory=utc_now, sa_column_kwargs={"onupdate": utc_now}
    )
