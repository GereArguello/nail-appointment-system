from datetime import datetime
from typing import Self

from pydantic import field_validator, model_validator
from sqlmodel import Field, SQLModel


class CalendarBlockCreate(SQLModel):
    starts_at: datetime
    ends_at: datetime
    reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_time_range(self) -> Self:
        if self.ends_at <= self.starts_at:
            raise ValueError(
                "La fecha de finalización debe ser posterior a la fecha de inicio"
            )

        if self.ends_at.date() != self.starts_at.date():
            raise ValueError("El bloqueo debe comenzar y finalizar el mismo día")

        return self

    @field_validator("starts_at", "ends_at")
    @classmethod
    def validate_naive_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is not None and value.utcoffset() is not None:
            raise ValueError("La fecha debe enviarse sin zona horaria")

        return value


class CalendarBlockRead(SQLModel):
    id: int
    starts_at: datetime
    ends_at: datetime
    reason: str | None
    created_at: datetime
