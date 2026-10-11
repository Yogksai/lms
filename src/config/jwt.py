from functools import lru_cache
from typing import Literal

from pydantic import Field

from src.config.base import EnvironmentSettings


class Settings(EnvironmentSettings):
    algorithm: Literal["HS256"] = Field("HS256", alias="JWT_ALGORITHM")
    issuer: str = Field("lms-api", alias="JWT_ISSUER")
    audience: str = Field("lms-client", alias="JWT_AUDIENCE")
    access_token_expire_seconds: int = Field(900, gt=0, alias="ACCESS_TOKEN_EXPIRE_SECONDS")
    refresh_token_expire_seconds: int = Field(2_592_000, gt=0, alias="REFRESH_TOKEN_EXPIRE_SECONDS")


@lru_cache
def get_settings() -> Settings:
    return Settings()
