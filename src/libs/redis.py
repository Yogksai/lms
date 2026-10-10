from typing import Annotated

from fastapi import Depends, Request
from redis.asyncio import Redis


def get_redis(request: Request) -> Redis:
    client: Redis = request.app.state.redis
    return client


IRedis = Annotated[Redis, Depends(get_redis)]
