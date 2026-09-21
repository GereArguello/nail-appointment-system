from datetime import datetime

from sqlmodel import Field, SQLModel

from app.business_settings.models import BusinessSettingsBase


class BusinessSettingsUpdate(SQLModel):
    appointment_start_tolerance_minutes: int | None = Field(
        default=None,
        ge=0,
    )
    appointment_end_tolerance_minutes: int | None = Field(
        default=None,
        ge=0,
    )
    appointment_cancellation_limit_hours: int | None = Field(default=None, ge=0)

    slot_interval_minutes: int | None = Field(
        default=None,
        ge=10,
        le=60,
        multiple_of=5,
    )

    deposit_payment_expiration_hours: int | None = Field(default=None, ge=1, le=168)


class BusinessSettingsRead(BusinessSettingsBase):
    id: int

    created_at: datetime
    updated_at: datetime
