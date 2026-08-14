from datetime import datetime

from sqlmodel import Field, SQLModel

from app.core.enums import StatusEnum
from app.utils import utc_now


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
