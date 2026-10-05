from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from src.auth.dto import UserDTO
from src.auth.entities import UserEntity
from src.auth.exceptions import CredentialsException
from src.auth.service.password import PasswordService
from src.auth.service.token import TokenService
from src.config.jwt import Settings as JwtSettings
from src.config.security import Settings as SecuritySettings


@pytest.fixture
def token_service() -> TokenService:
    return TokenService(
        JwtSettings(_env_file=None),
        SecuritySettings(_env_file=None, SECRET_KEY="test-only-key-" * 4),
    )


async def test_password_hashing_and_unicode_byte_limit() -> None:
    first = await PasswordService.get_password_hash("valid-password")
    second = await PasswordService.get_password_hash("valid-password")
    assert first != second
    assert await PasswordService.verify_password("valid-password", first)
    assert not await PasswordService.verify_password("wrong", first)
    assert not await PasswordService.verify_password("anything", None)
    with pytest.raises(ValueError):
        await PasswordService.get_password_hash("я" * 37)
    assert not await PasswordService.verify_password("a" * 73, first)


def test_entity_does_not_hash_or_mutate_credentials() -> None:
    entity = UserEntity(name="Student", email="student@example.com", password_hash="stored-hash")
    assert entity.password_hash == "stored-hash"
    public = UserDTO(id=1, name=entity.name, email=entity.email, is_active=True)
    assert "password_hash" not in public.model_dump()


def test_access_token_round_trip(token_service: TokenService) -> None:
    token = token_service.create_access_token(42, uuid4())
    assert token_service.verify_access_token(token.access_token).user_id == 42


@pytest.mark.parametrize("change", ["expired", "refresh", "wrong_audience", "invalid_subject"])
def test_invalid_claims_are_rejected(token_service: TokenService, change: str) -> None:
    token = token_service.create_access_token(42, uuid4()).access_token
    payload = jwt.decode(
        token,
        token_service.secret_key,
        algorithms=["HS256"],
        audience=token_service.settings.audience,
    )
    if change == "expired":
        payload["exp"] = datetime.now(UTC) - timedelta(seconds=1)
    elif change == "refresh":
        payload["token_type"] = "refresh"
    elif change == "wrong_audience":
        payload["aud"] = "another-client"
    else:
        payload["sub"] = "not-an-id"
    invalid = jwt.encode(payload, token_service.secret_key, algorithm="HS256")
    with pytest.raises(CredentialsException):
        token_service.verify_access_token(invalid)


def test_wrong_signature_is_rejected(token_service: TokenService) -> None:
    token = token_service.create_access_token(42, uuid4()).access_token
    different_service = TokenService(
        JwtSettings(_env_file=None),
        SecuritySettings(_env_file=None, SECRET_KEY="different-test-key-" * 3),
    )
    with pytest.raises(CredentialsException):
        different_service.verify_access_token(token)
