import re
from datetime import date, datetime
from typing import Self

from pydantic import ConfigDict, EmailStr, field_validator, model_validator
from sqlmodel import Field, SQLModel

from app.users.models import UserBase


class UserCreate(UserBase):
    email: EmailStr

    password: str = Field(min_length=8, max_length=128)
    password2: str = Field(min_length=8, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not re.search(r"[A-Z]", value):
            raise ValueError("La contraseña debe contener al menos una mayúscula")

        if not re.search(r"\d", value):
            raise ValueError("La contraseña debe contener al menos un número")

        return value

    @field_validator("birth_date")
    @classmethod
    def validate_birth_date(cls, value: date | None) -> date | None:
        if value is not None and value > date.today():
            raise ValueError("La fecha de nacimiento no puede ser futura")

        return value

    @model_validator(mode="after")
    def password_match(self) -> Self:
        if self.password != self.password2:
            raise ValueError("Las contraseñas no coinciden")
        return self


class UserRead(UserBase):
    id: int

    email: EmailStr
    created_at: datetime
    updated_at: datetime


class UserUpdate(SQLModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=50)
    last_name: str | None = Field(default=None, min_length=1, max_length=50)
    birth_date: date | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("birth_date")
    @classmethod
    def validate_birth_date(cls, value: date | None) -> date | None:
        if value is not None and value > date.today():
            raise ValueError("La fecha de nacimiento no puede ser futura")

        return value


class UserPasswordUpdate(SQLModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
    new_password2: str = Field(min_length=8, max_length=128)

    model_config = ConfigDict(extra="forbid")

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        if not re.search(r"[A-Z]", value):
            raise ValueError("La contraseña debe contener al menos una mayúscula")

        if not re.search(r"\d", value):
            raise ValueError("La contraseña debe contener al menos un número")

        return value

    @model_validator(mode="after")
    def passwords_match(self) -> Self:
        if self.new_password != self.new_password2:
            raise ValueError("Las contraseñas nuevas no coinciden")

        if self.current_password == self.new_password:
            raise ValueError("La contraseña nueva debe ser diferente de la actual")

        return self
