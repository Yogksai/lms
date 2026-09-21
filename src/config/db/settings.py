from functools import lru_cache

from pydantic import Field, SecretStr
from sqlalchemy import URL

from src.config.base import EnvironmentSettings


class Settings(EnvironmentSettings):
    host: str = Field("127.0.0.1", alias="DB_HOST")
    port: int = Field(5432, ge=1, le=65535, alias="DB_PORT")
    name: str = Field("lms", alias="DB_NAME")
    user: str = Field("lms", alias="DB_USER")
    password: SecretStr = Field(SecretStr("lms-local"), alias="DB_PASSWORD")
    echo: bool = Field(False, alias="DB_ECHO_LOG")
    pool_size: int = Field(5, gt=0, alias="DB_POOL_SIZE")
    max_overflow: int = Field(5, ge=0, alias="DB_MAX_OVERFLOW")
    connect_timeout: float = Field(5.0, gt=0, alias="DB_CONNECT_TIMEOUT")
    command_timeout: float = Field(5.0, gt=0, alias="DB_COMMAND_TIMEOUT")

    @property
    def database_url(self) -> URL:
        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.user,
            password=self.password.get_secret_value(),
            host=self.host,
            port=self.port,
            database=self.name,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
