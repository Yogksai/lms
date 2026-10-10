from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis.asyncio import Redis

from src.config.db.engine import DatabaseHelper
from src.config.db.settings import get_settings as get_database_settings
from src.config.redis import get_settings as get_redis_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    database = DatabaseHelper(get_database_settings())
    settings = get_redis_settings()
    redis = Redis.from_url(
        settings.url.get_secret_value(),
        decode_responses=True,
        socket_connect_timeout=settings.timeout,
        socket_timeout=settings.timeout,
    )
    app.state.database = database
    app.state.redis = redis
    try:
        yield
    finally:
        try:
            await redis.aclose()
        finally:
            await database.dispose()
