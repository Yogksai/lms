import pytest
from pydantic import ValidationError

from src.config.cors import Settings as CorsSettings
from src.config.db.settings import Settings as DatabaseSettings
from src.config.project import Settings as ProjectSettings
from src.config.security import Settings as SecuritySettings


def test_database_url_preserves_special_characters() -> None:
    settings = DatabaseSettings(_env_file=None, DB_PASSWORD="p@ss:/%word")
    assert settings.database_url.password == "p@ss:/%word"
    assert "p@ss" not in str(settings.database_url)


def test_port_range_is_validated() -> None:
    with pytest.raises(ValidationError):
        ProjectSettings(_env_file=None, APP_PORT=70000)


def test_cors_json_and_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", '["https://lms.example"]')
    settings = CorsSettings(_env_file=None)
    assert settings.allow_origins == ["https://lms.example"]
    with pytest.raises(ValidationError):
        CorsSettings(_env_file=None, CORS_ALLOW_ORIGINS=["*"], CORS_ALLOW_CREDENTIALS=True)


def test_short_signing_key_is_rejected() -> None:
    with pytest.raises(ValidationError):
        SecuritySettings(_env_file=None, SECRET_KEY="short")
