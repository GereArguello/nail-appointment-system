from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, ForeignKey
from sqlmodel import Field, Relationship, SQLModel

from app.core.datetime import utc_now
from app.core.enums import AppointmentStatusEnum

if TYPE_CHECKING:
    from app.services.models import Service
    from app.users.models import User


class Appointment(SQLModel, table=True):  # type: ignore[call-arg]
    id: int | None = Field(default=None, primary_key=True)

    user_id: int = Field(sa_column=Column(ForeignKey("user.id"), nullable=False))
    service_id: int = Field(sa_column=Column(ForeignKey("service.id"), nullable=False))

    starts_at: datetime
    ends_at: datetime

    status: AppointmentStatusEnum

    agreed_price: int = Field(ge=0)
    agreed_deposit: int = Field(default=0, ge=0)
    payment_expires_at: datetime | None = None

    description: str | None = Field(default=None, max_length=500)

    created_at: datetime = Field(
        default_factory=utc_now,
        sa_type=DateTime(timezone=True),
    )

    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"onupdate": utc_now},
    )

    user: "User" = Relationship(back_populates="appointments")
    service: "Service" = Relationship(back_populates="appointments")
