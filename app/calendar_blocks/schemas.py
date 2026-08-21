from datetime import datetime
from typing import Self

from pydantic import field_validator, model_validator
from sqlmodel import Field, SQLModel

from app.utils import utc_now


class CalendarBlockCreate(SQLModel):
    starts_at: datetime
    ends_at: datetime
    reason: str | None = Field(default=None, max_length=500)

    @field_validator("starts_at")
    @classmethod
    def validate_starts_at(cls, value: datetime) -> datetime:
        now = utc_now()

        if value < now:
            raise ValueError(
                "La fecha de inicio no puede ser anterior al momento actual"
            )

        return value

    @model_validator(mode="after")
    def validate_time_range(self) -> Self:
        if self.ends_at <= self.starts_at:
            raise ValueError(
                "La fecha de finalización debe ser posterior a la fecha de inicio"
            )

        if self.ends_at.date() != self.starts_at.date():
            raise ValueError("El bloqueo debe comenzar y finalizar el mismo día")

        return self


class CalendarBlockRead(SQLModel):
    id: int
    starts_at: datetime
    ends_at: datetime
    reason: str | None
    created_at: datetime
