from functools import lru_cache

from pydantic import Field, SecretStr

from src.config.base import EnvironmentSettings


class Settings(EnvironmentSettings):
    secret_key: SecretStr = Field(min_length=32, alias="SECRET_KEY")


@lru_cache
def get_settings() -> Settings:
    return Settings()
