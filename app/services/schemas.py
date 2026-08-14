from datetime import datetime
from typing import Self

from pydantic import field_validator, model_validator
from sqlmodel import Field, SQLModel

from app.core.enums import StatusEnum


class ServiceCreate(SQLModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=500)

    duration_minutes: int = Field(gt=0)
    buffer_before_minutes: int = Field(default=0, ge=0)
    buffer_after_minutes: int = Field(default=0, ge=0)

    price: int = Field(gt=0)
    deposit_amount: int = Field(default=0, ge=0)

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

    @model_validator(mode="after")
    def validate_deposit_amount(self) -> Self:
        if self.deposit_amount > self.price:
            raise ValueError("El depósito no puede ser mayor al precio")
        return self


class ServiceRead(SQLModel):
    id: int

    name: str
    description: str | None

    duration_minutes: int
    buffer_before_minutes: int
    buffer_after_minutes: int

    price: int
    deposit_amount: int

    status: StatusEnum

    created_at: datetime
    updated_at: datetime
