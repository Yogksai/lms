from functools import lru_cache

from pydantic import Field

from src.config.base import EnvironmentSettings


class Settings(EnvironmentSettings):
    host: str = Field("127.0.0.1", alias="APP_HOST")
    port: int = Field(8000, ge=1, le=65535, alias="APP_PORT")
    title: str = Field("LMS API", alias="APP_TITLE")
    version: str = Field("0.1.0", alias="APP_VERSION")
    root_path: str = Field("", alias="APP_ROOT_PATH")
    debug: bool = Field(False, alias="APP_DEBUG")


@lru_cache
def get_settings() -> Settings:
    return Settings()
