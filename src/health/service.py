import asyncio
import logging
from collections.abc import Awaitable
from typing import cast

from src.config.db.session import IDatabaseHelper
from src.libs.redis import IRedis

logger = logging.getLogger(__name__)


class HealthService:
    def __init__(self, database: IDatabaseHelper, redis: IRedis) -> None:
        self.database = database
        self.redis = redis

    async def is_ready(self) -> bool:
        try:
            async with asyncio.timeout(6):
                await self.database.check_connection()
        except Exception:
            logger.warning("Database readiness check failed")
            return False
        try:
            async with asyncio.timeout(2):
                await cast(Awaitable[bool], self.redis.ping())
        except Exception:
            logger.warning("Redis unavailable; optional quiz acceleration is degraded")
        return True
