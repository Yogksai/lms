import asyncio

from redis.asyncio import Redis

from src.config.db.engine import DatabaseHelper
from src.config.db.settings import get_settings as get_database_settings
from src.config.redis import get_settings as get_redis_settings
from src.health.service import HealthService


async def check() -> None:
    database = DatabaseHelper(get_database_settings())
    settings = get_redis_settings()
    redis = Redis.from_url(
        settings.url.get_secret_value(),
        socket_connect_timeout=settings.timeout,
        socket_timeout=settings.timeout,
    )
    try:
        if not await HealthService(database, redis).is_ready():
            raise SystemExit("Backend dependencies are unavailable")
    finally:
        try:
            await redis.aclose()
        finally:
            await database.dispose()


if __name__ == "__main__":
    asyncio.run(check())
