from datetime import datetime

from pydantic import field_validator
from sqlmodel import Field, SQLModel

from app.core.enums import AppointmentStatusEnum


class AppointmentCreate(SQLModel):
    service_id: int
    starts_at: datetime
    description: str | None = Field(default=None, max_length=500)

    @field_validator("starts_at")
    @classmethod
    def validate_starts_at(cls, value: datetime) -> datetime:
        if value.tzinfo is not None:
            raise ValueError("starts_at debe enviarse sin zona horaria")

        return value

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class AppointmentRead(SQLModel):
    id: int
    user_id: int
    service_id: int

    starts_at: datetime
    ends_at: datetime

    status: AppointmentStatusEnum

    agreed_price: int
    agreed_deposit: int
    payment_expires_at: datetime | None

    description: str | None

    created_at: datetime
    updated_at: datetime
