"""Redis cache management and utilities."""

import json
import logging
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

import redis.asyncio as redis
from redis.asyncio import Redis

from .config import get_settings

logger = logging.getLogger(__name__)
T = TypeVar("T")


class CacheManager:
    """Redis cache manager with connection pooling."""

    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        self._client: Optional[Redis] = None
        self.default_ttl = self.settings.cache_default_ttl

    async def get_client(self) -> Redis:
        """Get Redis client with connection pooling."""
        if not self._client:
            self._client = redis.from_url(
                self.settings.redis_url,
                encoding="utf-8",
                decode_responses=False,  # We'll handle encoding ourselves
                max_connections=self.settings.cache_max_connections,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=30,
            )
        return self._client

    async def set(
        self, key: str, value: Any, expire: Optional[int] = None, serialize: bool = True
    ) -> bool:
        """Set a value in Redis cache."""
        try:
            client = await self.get_client()
            if serialize:
                value = json.dumps(value, default=str)
            return await client.set(key, value, ex=expire or self.default_ttl)
        except Exception as e:
            logger.error(f"Redis set error for key {key}: {e}")
            return False

    async def get(self, key: str, deserialize: bool = True) -> Optional[Any]:
        """Get a value from Redis cache."""
        try:
            client = await self.get_client()
            value = await client.get(key)
            if value is None:
                return None

            if deserialize:
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value.decode("utf-8")
            return value
        except Exception as e:
            logger.error(f"Redis get error for key {key}: {e}")
            return None

    async def delete(self, key: str) -> bool:
        """Delete a key from Redis cache."""
        try:
            client = await self.get_client()
            return await client.delete(key) > 0
        except Exception as e:
            logger.error(f"Redis delete error for key {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if a key exists in Redis cache."""
        try:
            client = await self.get_client()
            return await client.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis exists error for key {key}: {e}")
            return False

    async def get_or_set(
        self, key: str, factory: Callable[[], T], ttl: Optional[int] = None
    ) -> T:
        """Get value from cache or set it using factory function."""
        cached_value = await self.get(key)
        if cached_value is not None:
            logger.debug(f"Cache hit for key: {key}")
            return cached_value

        logger.debug(f"Cache miss for key: {key}")
        value = await factory() if callable(factory) else factory
        await self.set(key, value, expire=ttl)
        return value

    async def health_check(self) -> bool:
        """Check Redis connection health."""
        try:
            client = await self.get_client()
            await client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False


def cached(prefix: str, ttl: Optional[int] = None, key_func: Optional[Callable] = None):
    """Decorator for caching function results."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            # Get cache manager from dependency injection
            cache_manager = kwargs.get("cache_manager")
            if not cache_manager:
                return await func(*args, **kwargs)

            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{prefix}:{hash(str(args) + str(kwargs))}"

            return await cache_manager.get_or_set(
                cache_key, lambda: func(*args, **kwargs), ttl
            )

        return wrapper

    return decorator
