from datetime import datetime

from core.enums import RoleEnum, StatusEnum
from sqlalchemy import String
from sqlmodel import Column, Field, SQLModel

from app.utils import utc_now


class User(SQLModel, table=True):  # type: ignore[call-arg]
    __tablename__ = "users"
    id: int | None = Field(default=None, primary_key=True)

    first_name: str = Field(sa_column=Column(String(50)), nullable=False)
    last_name: str = Field(sa_column=Column(String(50)), nullable=False)

    email: str = Field(
        sa_column=Column(String(255), index=True, unique=True, nullable=False)
    )

    password_hash: str = Field(nullable=False)

    role: RoleEnum = Field(default=RoleEnum.CUSTOMER)
    status: StatusEnum = Field(default=StatusEnum.ACTIVE)

    email_verified: bool = Field(default=False)
    email_verified_at: datetime | None = Field(default=None)

    created_at: datetime = Field(default_factory=utc_now)

    updated_at: datetime | None = Field(
        default_factory=utc_now, sa_column_kwargs={"onupdate": utc_now}
    )
