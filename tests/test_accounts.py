from dataclasses import replace
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from src.app import get_app
from src.auth.dto import (
    LoginDTO,
    ProfileUpdateDTO,
    RegisterDTO,
    TokenPairDTO,
    UserCredentialsDTO,
    UserDTO,
)
from src.auth.exceptions import CredentialsException, UserAlreadyExists
from src.auth.repositories.session import SessionRecord, SessionRepo
from src.auth.repositories.user import UserRepo
from src.auth.service.account import DUMMY_PASSWORD_HASH, AccountService
from src.auth.service.password import PasswordService
from src.auth.service.token import TokenService
from src.config.jwt import Settings as JwtSettings
from src.config.security import Settings as SecuritySettings


@pytest.fixture
def tokens() -> TokenService:
    return TokenService(
        JwtSettings(_env_file=None),
        SecuritySettings(_env_file=None, SECRET_KEY="test-only-key-" * 4),
    )


@pytest.fixture
def account(tokens: TokenService) -> AccountService:
    session = MagicMock(spec=AsyncSession)
    users = AsyncMock(spec=UserRepo)
    sessions = AsyncMock(spec=SessionRepo)
    passwords = AsyncMock(spec=PasswordService)
    users.get.return_value = UserDTO(
        id=1, name="Student", email="student@example.com", is_active=True
    )
    users.create.return_value = users.get.return_value
    users.update_name.return_value = users.get.return_value
    users.find_credentials.return_value = UserCredentialsDTO(
        **users.get.return_value.model_dump(), password_hash="stored-hash"
    )
    sessions.is_active.return_value = True
    sessions.find_refresh.return_value = SessionRecord(
        id=10,
        user_id=1,
        session_key=uuid4(),
        expires_at=datetime.now(UTC) + timedelta(days=30),
        revoked_at=None,
        consumed_at=None,
    )
    passwords.get_password_hash.return_value = "stored-hash"
    passwords.verify_password.return_value = True
    return AccountService(session, users, sessions, tokens, passwords)


async def test_registration_hashes_password_and_creates_active_account(
    account: AccountService,
) -> None:
    data = RegisterDTO(name=" Student ", email="Student@Example.com", password="strong-password")
    user = await account.register(data)
    entity = account.users.create.call_args.args[0]
    assert entity.email == "student@example.com"
    assert entity.name == "Student"
    assert entity.password_hash == "stored-hash"
    assert entity.is_active
    assert "password_hash" not in user.model_dump()
    account.passwords.get_password_hash.assert_awaited_once_with("strong-password")
    account.session.begin.return_value.__aexit__.assert_awaited_once_with(None, None, None)


async def test_duplicate_registration_rolls_back(account: AccountService) -> None:
    account.users.create.side_effect = UserAlreadyExists
    with pytest.raises(UserAlreadyExists):
        await account.register(
            RegisterDTO(name="Student", email="student@example.com", password="strong-password")
        )
    assert account.session.begin.return_value.__aexit__.call_args.args[0] is UserAlreadyExists


async def test_login_stores_only_refresh_hash_and_binds_access_session(
    account: AccountService,
) -> None:
    pair = await account.login(LoginDTO(email="Student@Example.com", password="strong-password"))
    user_id, session_key, expires_at, digest = account.sessions.create.call_args.args
    assert user_id == 1
    assert digest == account.tokens.hash_refresh_token(pair.refresh_token)
    assert digest != pair.refresh_token
    assert len(pair.refresh_token) == 43
    assert expires_at > datetime.now(UTC)
    payload = account.tokens.verify_access_token(pair.access_token)
    assert payload.session_id == session_key
    assert pair.expires_in == 900
    assert pair.refresh_expires_in == 2592000


@pytest.mark.parametrize("reason", ["missing", "disabled", "passwordless", "wrong-password"])
async def test_login_failure_is_uniform(account: AccountService, reason: str) -> None:
    if reason == "missing":
        account.users.find_credentials.return_value = None
    elif reason == "disabled":
        account.users.find_credentials.return_value.is_active = False
    elif reason == "passwordless":
        account.users.find_credentials.return_value.password_hash = None
    else:
        account.passwords.verify_password.return_value = False
    with pytest.raises(CredentialsException):
        await account.login(LoginDTO(email="student@example.com", password="strong-password"))
    account.sessions.create.assert_not_awaited()
    account.passwords.verify_password.assert_awaited_once()
    if reason in {"missing", "passwordless"}:
        assert account.passwords.verify_password.call_args.args[1] == DUMMY_PASSWORD_HASH


async def test_dummy_password_hash_is_valid() -> None:
    assert not await PasswordService.verify_password("not-the-dummy-password", DUMMY_PASSWORD_HASH)


async def test_refresh_rotates_without_extending_session(account: AccountService) -> None:
    record = account.sessions.find_refresh.return_value
    previous = account.tokens.create_refresh_token()
    pair = await account.refresh(previous)
    assert pair.refresh_token != previous
    account.sessions.consume.assert_awaited_once()
    assert account.sessions.consume.call_args.args[0] == account.tokens.hash_refresh_token(previous)
    account.sessions.add_refresh.assert_awaited_once_with(
        record.id, account.tokens.hash_refresh_token(pair.refresh_token)
    )
    assert account.tokens.verify_access_token(pair.access_token).session_id == record.session_key
    assert 0 < pair.refresh_expires_in <= 2592000
    account.sessions.revoke.assert_not_awaited()


@pytest.mark.parametrize("reason", ["reused", "revoked", "expired", "disabled", "missing-user"])
async def test_invalid_refresh_commits_revocation_before_401(
    account: AccountService, reason: str
) -> None:
    now = datetime.now(UTC)
    record = account.sessions.find_refresh.return_value
    if reason == "reused":
        record = replace(record, consumed_at=now)
    elif reason == "revoked":
        record = replace(record, revoked_at=now)
    elif reason == "expired":
        record = replace(record, expires_at=now - timedelta(seconds=1))
    elif reason == "disabled":
        account.users.get.return_value.is_active = False
    else:
        account.users.get.return_value = None
    account.sessions.find_refresh.return_value = record
    with pytest.raises(CredentialsException):
        await account.refresh(account.tokens.create_refresh_token())
    account.sessions.revoke.assert_awaited_once()
    account.sessions.add_refresh.assert_not_awaited()
    account.session.begin.return_value.__aexit__.assert_awaited_once_with(None, None, None)


async def test_unknown_refresh_is_rejected(account: AccountService) -> None:
    account.sessions.find_refresh.return_value = None
    with pytest.raises(CredentialsException):
        await account.refresh("x" * 43)
    account.sessions.revoke.assert_not_awaited()


async def test_logout_revokes_session_and_is_idempotent(account: AccountService) -> None:
    await account.logout("x" * 43)
    account.sessions.revoke.assert_awaited_once()
    account.sessions.find_refresh.return_value = None
    await account.logout("unknown".ljust(43, "x"))
    assert account.sessions.revoke.await_count == 1


@pytest.mark.parametrize("reason", ["revoked-session", "disabled-user", "missing-user"])
async def test_current_user_checks_session_and_account(
    account: AccountService, reason: str
) -> None:
    if reason == "revoked-session":
        account.sessions.is_active.return_value = False
    elif reason == "disabled-user":
        account.users.get.return_value.is_active = False
    else:
        account.users.get.return_value = None
    with pytest.raises(CredentialsException):
        await account.current_user(account.tokens.create_access_token(1, uuid4()).access_token)


async def test_current_user_and_profile_use_separate_transactions(account: AccountService) -> None:
    user = await account.current_user(account.tokens.create_access_token(1, uuid4()).access_token)
    await account.update_profile(user.id, ProfileUpdateDTO(name="Updated"))
    assert account.session.begin.call_count == 2
    account.users.update_name.assert_awaited_once_with(1, "Updated")
    account.users.update_name.return_value = None
    with pytest.raises(CredentialsException):
        await account.update_profile(user.id, ProfileUpdateDTO(name="Updated"))


@pytest.mark.parametrize("password", ["short", "a" * 73, "я" * 37])
def test_registration_password_limits(password: str) -> None:
    with pytest.raises(ValidationError):
        RegisterDTO(name="Student", email="student@example.com", password=password)


@pytest.mark.parametrize("claim", [None, 5, [], "not-a-uuid"])
def test_invalid_session_claims(tokens: TokenService, claim: object) -> None:
    valid = tokens.create_access_token(1, uuid4()).access_token
    claims = jwt.decode(
        valid, tokens.secret_key, algorithms=["HS256"], audience=tokens.settings.audience
    )
    claims["sid"] = claim
    invalid = jwt.encode(claims, tokens.secret_key, algorithm="HS256")
    with pytest.raises(CredentialsException):
        tokens.verify_access_token(invalid)


def test_refresh_tokens_are_unique_and_one_way_hashed(tokens: TokenService) -> None:
    first, second = tokens.create_refresh_token(), tokens.create_refresh_token()
    assert first != second
    assert len(tokens.hash_refresh_token(first)) == 64
    assert tokens.hash_refresh_token(first) == tokens.hash_refresh_token(first)


@pytest.fixture
def client() -> TestClient:
    app = get_app()
    service = AsyncMock(spec=AccountService)
    user = UserDTO(id=1, name="Student", email="student@example.com", is_active=True)
    service.register.return_value = user
    service.current_user.return_value = user
    service.update_profile.return_value = user.model_copy(update={"name": "Updated"})
    service.login.return_value = TokenPairDTO(
        access_token="access", refresh_token="x" * 43, expires_in=900, refresh_expires_in=2592000
    )
    service.refresh.return_value = service.login.return_value
    app.dependency_overrides[AccountService] = lambda: service
    return TestClient(app)


def test_account_endpoints_and_no_store(client: TestClient) -> None:
    registration = client.post(
        "/v1/auth/register",
        json={"name": "Student", "email": "student@example.com", "password": "strong-password"},
    )
    assert registration.status_code == 201
    assert "password" not in registration.text
    for path, data in [
        ("/login", {"email": "student@example.com", "password": "strong-password"}),
        ("/refresh", {"refresh_token": "x" * 43}),
    ]:
        response = client.post("/v1/auth" + path, json=data)
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store"
    logout = client.post("/v1/auth/logout", json={"refresh_token": "x" * 43})
    assert logout.status_code == 204
    assert logout.content == b""
    assert client.get("/v1/auth/me").status_code == 401
    headers = {"Authorization": "Bearer access"}
    assert client.get("/v1/auth/me", headers=headers).json()["id"] == 1
    assert (
        client.patch("/v1/auth/me", headers=headers, json={"name": "Updated"}).json()["name"]
        == "Updated"
    )
    assert (
        client.patch(
            "/v1/auth/me", headers=headers, json={"name": "Updated", "is_active": True}
        ).status_code
        == 422
    )


def test_validation_does_not_echo_secrets(client: TestClient) -> None:
    password = "sensitive-password-value" * 5
    response = client.post(
        "/v1/auth/register",
        json={"name": "Student", "email": "student@example.com", "password": password},
    )
    assert response.status_code == 422
    assert password not in response.text
    assert "input" not in response.text
    response = client.post("/v1/auth/refresh", json={"refresh_token": "sensitive-invalid-token"})
    assert response.status_code == 422
    assert "sensitive-invalid-token" not in response.text


def test_duplicate_and_invalid_credentials_http_contracts() -> None:
    app = get_app()
    service = AsyncMock(spec=AccountService)
    service.register.side_effect = UserAlreadyExists
    service.login.side_effect = CredentialsException
    app.dependency_overrides[AccountService] = lambda: service
    client = TestClient(app)
    assert (
        client.post(
            "/v1/auth/register",
            json={"name": "Student", "email": "student@example.com", "password": "strong-password"},
        ).status_code
        == 409
    )
    response = client.post(
        "/v1/auth/login", json={"email": "student@example.com", "password": "strong-password"}
    )
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


async def test_refresh_lookup_locks_parent_session_before_reading_consumption() -> None:
    session = MagicMock(spec=AsyncSession)
    result = MagicMock()
    result.scalar_one_or_none.return_value = MagicMock(
        id=10,
        user_id=1,
        session_key=uuid4(),
        expires_at=datetime.now(UTC) + timedelta(days=1),
        revoked_at=None,
    )
    session.execute.return_value = result
    consumed_at = datetime.now(UTC)
    session.scalar.return_value = consumed_at
    record = await SessionRepo(session).find_refresh("a" * 64)
    assert record is not None and record.consumed_at == consumed_at
    sql = str(session.execute.call_args.args[0].compile(dialect=postgresql.dialect()))
    assert "FOR UPDATE OF auth_sessions" in sql
    assert "refresh_tokens.token_hash" in sql


async def test_active_session_query_checks_user_revocation_and_expiry() -> None:
    session = AsyncMock()
    session.scalar.return_value = None
    assert not await SessionRepo(session).is_active(uuid4(), 1, datetime.now(UTC))
    sql = str(session.scalar.call_args.args[0].compile(dialect=postgresql.dialect()))
    assert "auth_sessions.user_id" in sql
    assert "auth_sessions.revoked_at IS NULL" in sql
    assert "auth_sessions.expires_at >" in sql
