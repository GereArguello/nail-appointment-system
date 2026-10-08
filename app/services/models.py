from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime
from sqlmodel import Field, Relationship, SQLModel

from app.core.datetime import utc_now
from app.core.enums import StatusEnum

if TYPE_CHECKING:
    from app.appointments.models import Appointment


class Service(SQLModel, table=True):  # type: ignore[call-arg]
    id: int | None = Field(default=None, primary_key=True)

    name: str = Field(max_length=200, unique=True)
    description: str | None = Field(default=None, max_length=500)

    duration_minutes: int = Field(gt=0)
    buffer_before_minutes: int = Field(default=0, ge=0)
    buffer_after_minutes: int = Field(default=0, ge=0)

    price: int = Field(gt=0)
    deposit_amount: int = Field(default=0, ge=0)

    status: StatusEnum = Field(default=StatusEnum.ACTIVE)

    created_at: datetime = Field(
        default_factory=utc_now,
        sa_type=DateTime(timezone=True),
    )

    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"onupdate": utc_now},
    )

    appointments: list["Appointment"] = Relationship(back_populates="service")
