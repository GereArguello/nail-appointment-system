from datetime import datetime

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel

from app.core.datetime import utc_now


class CalendarBlock(SQLModel, table=True):  # type: ignore[call-arg]
    id: int | None = Field(default=None, primary_key=True)

    starts_at: datetime = Field(
        sa_type=DateTime(timezone=True),
    )

    ends_at: datetime = Field(
        sa_type=DateTime(timezone=True),
    )

    reason: str | None = Field(default=None, max_length=500)

    created_at: datetime = Field(
        default_factory=utc_now,
        sa_type=DateTime(timezone=True),
    )
