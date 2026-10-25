from functools import lru_cache

from pydantic import Field, SecretStr

from src.config.base import EnvironmentSettings


class Settings(EnvironmentSettings):
    host: str = Field("127.0.0.1", alias="RABBITMQ_HOST")
    port: int = Field(5672, ge=1, le=65535, alias="RABBITMQ_PORT")
    username: str = Field("lms", alias="RABBITMQ_USER")
    password: SecretStr = Field(SecretStr("lms-local"), alias="RABBITMQ_PASSWORD")
    virtual_host: str = Field("/", alias="RABBITMQ_VHOST")
    tls: bool = Field(False, alias="RABBITMQ_TLS")
    queue: str = Field("lms.learning.events", alias="RABBITMQ_QUEUE")
    retries: int = Field(5, ge=0, le=20, alias="RABBITMQ_RETRIES")
    timeout: float = Field(5, gt=0, le=60, alias="RABBITMQ_TIMEOUT")


@lru_cache
def get_settings() -> Settings:
    return Settings()
