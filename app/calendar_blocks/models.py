from datetime import datetime

from sqlmodel import Field, SQLModel

from app.utils import utc_now


class CalendarBlocks(SQLModel, table=True):  # type: ignore[call-arg]
    id: int | None = Field(default=None, primary_key=True)
    starts_at: datetime
    ends_at: datetime
    reason: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=utc_now)
