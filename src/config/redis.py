from functools import lru_cache

from pydantic import Field, SecretStr

from src.config.base import EnvironmentSettings


class Settings(EnvironmentSettings):
    url: SecretStr = Field(SecretStr("redis://127.0.0.1:6379/0"), alias="REDIS_URL")
    timeout: float = Field(2.0, gt=0, alias="REDIS_TIMEOUT")


@lru_cache
def get_settings() -> Settings:
    return Settings()
