from datetime import datetime

from sqlmodel import Field, SQLModel

from app.core.enums import AppointmentStatusEnum


class AppointmentCreate(SQLModel):
    service_id: int
    starts_at: datetime
    description: str | None = Field(default=None, max_length=500)


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
