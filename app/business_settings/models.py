from sqlmodel import Field, SQLModel


class BusinessSettings(SQLModel):
    appointment_end_tolerance_minutes: int = Field(default=0, ge=0)
