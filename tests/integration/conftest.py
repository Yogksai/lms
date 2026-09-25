import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.db.engine import DatabaseHelper
from src.config.db.settings import Settings


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    if os.getenv("LMS_INTEGRATION_TESTS") != "1":
        pytest.skip("PostgreSQL integration tests are not enabled")
    settings = Settings(_env_file=None)
    if not settings.name.startswith("lms_test"):
        pytest.fail("Integration tests require a dedicated DB_NAME starting with lms_test")
    helper = DatabaseHelper(settings)
    try:
        async with helper.engine.connect() as connection:
            transaction = await connection.begin()
            async with AsyncSession(
                bind=connection,
                join_transaction_mode="create_savepoint",
                expire_on_commit=False,
            ) as db_session:
                try:
                    yield db_session
                finally:
                    await db_session.rollback()
                    await transaction.rollback()
    finally:
        await helper.dispose()
