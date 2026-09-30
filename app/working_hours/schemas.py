from datetime import date as Date
from datetime import time
from typing import Self

from pydantic import model_validator
from sqlmodel import SQLModel

from app.core.enums import StatusEnum


class WorkingHourCreate(SQLModel):
    date: Date
    start_time: time
    end_time: time

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
