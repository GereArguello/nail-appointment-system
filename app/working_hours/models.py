from datetime import date as Date
from datetime import time

from sqlmodel import Field, SQLModel

from app.core.enums import StatusEnum


class WorkingHours(SQLModel, table=True):  # type: ignore[call-arg]
    id: int | None = Field(default=None, primary_key=True)

    date: Date = Field(unique=True)
    start_time: time
    end_time: time
    status: StatusEnum = Field(default=StatusEnum.ACTIVE)
