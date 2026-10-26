import logging
from collections.abc import Awaitable
from typing import Annotated, cast

from fastapi import Depends
from pydantic import TypeAdapter, ValidationError
from redis.exceptions import RedisError

from src.config.learning import get_settings
from src.libs.redis import IRedis
from src.quizzes.dto import SnapshotQuestion

logger = logging.getLogger(__name__)
pool_adapter = TypeAdapter(list[SnapshotQuestion])
START_SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then redis.call('EXPIRE', KEYS[1], 60) end
return count
"""


class QuizCache:
    def __init__(self, redis: IRedis) -> None:
        self.redis = redis

    async def allow_start(self, user_id: int) -> bool:
        try:
            result = await cast(
                Awaitable[int], self.redis.eval(START_SCRIPT, 1, f"quiz:starts:{user_id}")
            )
            return int(result) <= get_settings().starts_per_minute
        except RedisError, OSError:
            logger.warning("Quiz burst limiter unavailable; PostgreSQL daily cap remains active")
            return True

    @staticmethod
    def key(quiz_id: int, revision: int, course_revision: int) -> str:
        return f"quiz:pool:v1:{quiz_id}:{revision}:{course_revision}"

    async def load(self, key: str) -> list[SnapshotQuestion] | None:
        try:
            raw = await self.redis.get(key)
            return pool_adapter.validate_json(raw) if raw else None
        except RedisError, OSError, ValidationError, ValueError:
            logger.warning("Quiz pool cache miss or unavailable")
            return None

    async def save(self, key: str, pool: list[SnapshotQuestion]) -> None:
        try:
            await self.redis.set(key, pool_adapter.dump_json(pool), ex=get_settings().cache_seconds)
        except RedisError, OSError:
            logger.warning("Quiz pool cache write unavailable")


IQuizCache = Annotated[QuizCache, Depends()]
