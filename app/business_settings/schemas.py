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


class BusinessSettingsRead(BusinessSettingsBase):
    id: int

    created_at: datetime
    updated_at: datetime
