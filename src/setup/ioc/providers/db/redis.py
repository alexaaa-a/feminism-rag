from collections.abc import AsyncIterable

import redis.asyncio as redis
from dishka import Provider, Scope, provide

from src.application.interfaces.db.cache import CacheInterface
from src.config import Settings
from src.infrastructure.redis.cache import RedisCache


class RedisProvider(Provider):
    @provide(scope=Scope.APP)
    async def setup(self, settings: Settings) -> AsyncIterable[redis.Redis]:
        client = redis.Redis(
            host=settings.redis_settings.host,
            port=settings.redis_settings.port,
            db=settings.redis_settings.db,
            password=settings.redis_settings.password or None,
            decode_responses=True,
        )
        try:
            yield client
        finally:
            await client.aclose()


class RedisCacheProvider(Provider):
    cache = provide(RedisCache, provides=CacheInterface, scope=Scope.APP)
