from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.enums import TimezoneEnum


class Settings(BaseSettings):
    SECRET_KEY: str
    DATABASE_URL: str

    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    BUSINESS_TIMEZONE: TimezoneEnum = TimezoneEnum.BUENOS_AIRES

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
