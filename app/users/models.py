from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlmodel import Column, Field, Relationship, SQLModel

from app.core.enums import RoleEnum, StatusEnum
from app.utils import utc_now

if TYPE_CHECKING:
    from app.appointments.models import Appointment


class UserBase(SQLModel):
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    email: str = Field(min_length=3, max_length=255)
    birth_date: date | None = None


class User(UserBase, table=True):  # type: ignore[call-arg]
    id: int | None = Field(default=None, primary_key=True)

    email: str = Field(
        sa_column=Column(
            String(255),
            index=True,
            unique=True,
            nullable=False,
        )
    )

    password_hash: str = Field(nullable=False)

    role: RoleEnum = Field(default=RoleEnum.CUSTOMER)
    status: StatusEnum = Field(default=StatusEnum.ACTIVE)

    email_verified: bool = Field(default=False)
    email_verified_at: datetime | None = Field(default=None)

    created_at: datetime = Field(default_factory=utc_now)

    updated_at: datetime = Field(
        default_factory=utc_now, sa_column_kwargs={"onupdate": utc_now}
    )

    appointments: list["Appointment"] = Relationship(back_populates="user")
