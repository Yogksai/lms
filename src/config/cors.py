from functools import lru_cache

from pydantic import Field, model_validator

from src.config.base import EnvironmentSettings


class Settings(EnvironmentSettings):
    allow_origins: list[str] = Field(default_factory=list, alias="CORS_ALLOW_ORIGINS")
    allow_credentials: bool = Field(False, alias="CORS_ALLOW_CREDENTIALS")
    allow_methods: list[str] = Field(
        default_factory=lambda: ["GET", "POST", "PUT", "PATCH", "DELETE"],
        alias="CORS_ALLOW_METHODS",
    )
    allow_headers: list[str] = Field(
        default_factory=lambda: ["Authorization", "Content-Type"], alias="CORS_ALLOW_HEADERS"
    )

    @model_validator(mode="after")
    def validate_credential_origins(self) -> "Settings":
        if self.allow_credentials and "*" in self.allow_origins:
            raise ValueError("Credentialed CORS requires explicit origins")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
