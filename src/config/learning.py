from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_validator

from src.config.base import EnvironmentSettings


class Settings(EnvironmentSettings):
    daily_attempts: int = Field(5, ge=1, le=50, alias="QUIZ_DAILY_ATTEMPTS")
    timezone: str = Field("Asia/Almaty", alias="QUIZ_TIMEZONE")
    cache_seconds: int = Field(60, ge=1, le=3600, alias="QUIZ_CACHE_SECONDS")
    starts_per_minute: int = Field(20, ge=1, le=1000, alias="QUIZ_STARTS_PER_MINUTE")

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as error:
            raise ValueError("Unknown quiz reset timezone") from error
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
