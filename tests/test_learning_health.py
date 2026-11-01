from unittest.mock import AsyncMock

import pytest

from src.health.service import HealthService


@pytest.mark.parametrize(
    "db_down,redis_down,ready", [(False, False, True), (False, True, True), (True, False, False)]
)
async def test_database_is_required_but_quiz_cache_is_optional(
    db_down: bool, redis_down: bool, ready: bool
) -> None:
    database = AsyncMock()
    redis = AsyncMock()
    if db_down:
        database.check_connection.side_effect = OSError()
    if redis_down:
        redis.ping.side_effect = OSError()
    assert await HealthService(database, redis).is_ready() is ready
