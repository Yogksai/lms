import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.entities import UserEntity
from src.auth.exceptions import UserAlreadyExists
from src.auth.repositories.user import UserRepo

pytestmark = pytest.mark.integration


async def test_repository_round_trip(session: AsyncSession) -> None:
    repo = UserRepo(session)
    async with session.begin():
        created = await repo.create(
            UserEntity(name="Student", email="repository@example.com", password_hash="stored-hash")
        )
    loaded = await repo.get(created.id)
    assert loaded is not None
    assert loaded.email == "repository@example.com"
    assert not loaded.is_active
    assert "password_hash" not in loaded.model_dump()
    credentials = await repo.find_credentials(loaded.email)
    assert credentials is not None
    assert credentials.password_hash == "stored-hash"
    assert await repo.get(-1) is None


async def test_duplicate_failure_rolls_back_complete_use_case(session: AsyncSession) -> None:
    repo = UserRepo(session)
    with pytest.raises(UserAlreadyExists):
        async with session.begin():
            await repo.create(UserEntity(name="First", email="duplicate@example.com"))
            await repo.create(UserEntity(name="Second", email="duplicate@example.com"))
    assert await repo.find_credentials("duplicate@example.com") is None
    async with session.begin_nested():
        user = await repo.create(UserEntity(name="Recovery", email="recovery@example.com"))
    assert await repo.get(user.id) is not None


async def test_passwordless_account_is_supported(session: AsyncSession) -> None:
    repo = UserRepo(session)
    async with session.begin():
        user = await repo.create(UserEntity(name="OAuth Student", email="oauth@example.com"))
    credentials = await repo.find_credentials(user.email)
    assert credentials is not None
    assert credentials.password_hash is None
