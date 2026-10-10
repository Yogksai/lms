import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dto import LoginDTO, ProfileUpdateDTO, RegisterDTO
from src.auth.exceptions import CredentialsException, UserAlreadyExists
from src.auth.models.user import UserModel
from src.auth.repositories.session import SessionRepo
from src.auth.repositories.user import UserRepo
from src.auth.service.account import AccountService
from src.auth.service.password import PasswordService
from src.auth.service.token import TokenService
from src.config.jwt import Settings as JwtSettings
from src.config.security import Settings as SecuritySettings

pytestmark = pytest.mark.integration


@pytest.fixture
def accounts(session: AsyncSession) -> AccountService:
    tokens = TokenService(
        JwtSettings(_env_file=None),
        SecuritySettings(_env_file=None, SECRET_KEY="test-only-key-" * 4),
    )
    return AccountService(
        session, UserRepo(session), SessionRepo(session), tokens, PasswordService()
    )


async def test_register_login_rotate_logout_and_profile(accounts: AccountService) -> None:
    user = await accounts.register(
        RegisterDTO(name="Student", email="lifecycle@example.com", password="test-password")
    )
    pair = await accounts.login(LoginDTO(email="Lifecycle@example.com", password="test-password"))
    assert (await accounts.current_user(pair.access_token)).id == user.id
    profile = await accounts.update_profile(user.id, ProfileUpdateDTO(name="Updated"))
    assert profile.name == "Updated"
    replacement = await accounts.refresh(pair.refresh_token)
    assert replacement.refresh_token != pair.refresh_token
    assert (await accounts.current_user(replacement.access_token)).name == "Updated"
    await accounts.logout(replacement.refresh_token)
    await accounts.logout(replacement.refresh_token)
    with pytest.raises(CredentialsException):
        await accounts.current_user(pair.access_token)
    with pytest.raises(CredentialsException):
        await accounts.refresh(replacement.refresh_token)


async def test_refresh_reuse_revokes_only_its_session(accounts: AccountService) -> None:
    await accounts.register(
        RegisterDTO(name="Student", email="reuse@example.com", password="test-password")
    )
    login = LoginDTO(email="reuse@example.com", password="test-password")
    first = await accounts.login(login)
    second = await accounts.login(login)
    replacement = await accounts.refresh(first.refresh_token)
    with pytest.raises(CredentialsException):
        await accounts.refresh(first.refresh_token)
    with pytest.raises(CredentialsException):
        await accounts.current_user(replacement.access_token)
    assert (await accounts.current_user(second.access_token)).is_active


async def test_duplicate_email_and_disabled_account(
    accounts: AccountService, session: AsyncSession
) -> None:
    user = await accounts.register(
        RegisterDTO(name="Student", email="duplicate@example.com", password="test-password")
    )
    with pytest.raises(UserAlreadyExists):
        await accounts.register(
            RegisterDTO(name="Duplicate", email="Duplicate@Example.com", password="test-password")
        )
    login = LoginDTO(email="duplicate@example.com", password="test-password")
    pair = await accounts.login(login)
    async with session.begin():
        await session.execute(
            update(UserModel).where(UserModel.id == user.id).values(is_active=False)
        )
    with pytest.raises(CredentialsException):
        await accounts.login(login)
    with pytest.raises(CredentialsException):
        await accounts.current_user(pair.access_token)
    with pytest.raises(CredentialsException):
        await accounts.refresh(pair.refresh_token)
