from datetime import datetime
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from app.core.enums import StatusEnum
from app.utils import utc_now

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

    created_at: datetime = Field(default_factory=utc_now)

    updated_at: datetime = Field(
        default_factory=utc_now, sa_column_kwargs={"onupdate": utc_now}
    )

    appointments: list["Appointment"] = Relationship(back_populates="service")
