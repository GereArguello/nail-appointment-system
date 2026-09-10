from datetime import datetime

from sqlmodel import Field, SQLModel

from app.utils import utc_now


class BusinessSettingsBase(SQLModel):
    appointment_end_tolerance_minutes: int = Field(default=0, ge=0)


class BusinessSettings(BusinessSettingsBase, table=True):  # type: ignore[call-arg]
    id: int | None = Field(default=None, primary_key=True)

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(
        default_factory=utc_now, sa_column_kwargs={"onupdate": utc_now}
    )
