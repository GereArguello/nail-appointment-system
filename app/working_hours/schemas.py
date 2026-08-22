from datetime import date as Date
from datetime import time
from typing import Self

from pydantic import field_validator, model_validator
from sqlmodel import SQLModel

from app.core.enums import StatusEnum
from app.utils import utc_now


class WorkingHourCreate(SQLModel):
    date: Date
    start_time: time
    end_time: time

    @field_validator("date")
    @classmethod
    def validate_date(cls, value: Date) -> Date:
        today = utc_now().date()

        if value < today:
            raise ValueError("La fecha no puede ser anterior a hoy")

        return value

    @model_validator(mode="after")
    def validate_time_range(self) -> Self:
        if self.end_time <= self.start_time:
            raise ValueError(
                "La hora de finalización debe ser posterior a la hora de inicio"
            )

        return self


class WorkingHourRead(SQLModel):
    id: int
    date: Date
    start_time: time
    end_time: time
    status: StatusEnum
