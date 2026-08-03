import logging
from typing import Protocol

import redis.asyncio as redis_asyncio
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class CacheClient(Protocol):
    async def get(self, key: str) -> str | None: ...

    async def set(self, key: str, value: str, *, ttl_seconds: int) -> None: ...

    async def delete_prefix(self, prefix: str) -> None: ...

    async def close(self) -> None: ...


class RedisCacheClient:
    def __init__(self, url: str) -> None:
        self._redis = redis_asyncio.from_url(url, decode_responses=True)

    async def get(self, key: str) -> str | None:
        try:
            value = await self._redis.get(key)
            return str(value) if value is not None else None
        except RedisError:
            logger.warning("Redis GET failed for key %s, treating as cache miss.", key)
            return None

    async def set(self, key: str, value: str, *, ttl_seconds: int) -> None:
        try:
            await self._redis.set(key, value, ex=ttl_seconds)
        except RedisError:
            logger.warning("Redis SET failed for key %s.", key)

    async def delete_prefix(self, prefix: str) -> None:
        try:
            async for key in self._redis.scan_iter(match=f"{prefix}*"):
                await self._redis.delete(key)
        except RedisError:
            logger.warning("Redis invalidation failed for prefix %s.", prefix)

    async def close(self) -> None:
        await self._redis.aclose()


def task_list_cache_key(
    project_id: int,
    *,
    status: str | None,
    priority: str | None,
    assignee_id: int | None,
    page: int,
    limit: int,
) -> str:
    return (
        f"tasks:project:{project_id}:list:"
        f"status={status or 'any'}:priority={priority or 'any'}:"
        f"assignee={assignee_id if assignee_id is not None else 'any'}:"
        f"page={page}:limit={limit}"
    )


def task_list_cache_prefix(project_id: int) -> str:
    return f"tasks:project:{project_id}:list:"
