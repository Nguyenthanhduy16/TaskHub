import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.cache import RedisCacheClient
from app.core.config import get_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("Starting %s", app.title)
    settings = get_settings()
    app.state.cache_client = RedisCacheClient(settings.redis_url)
    yield
    await app.state.cache_client.close()
    logger.info("Stopping %s", app.title)
