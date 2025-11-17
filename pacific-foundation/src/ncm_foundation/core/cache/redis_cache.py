"""
Redis-based cache implementation for ncm-foundation.

This module provides comprehensive Redis caching functionality including:
- SQL query caching
- Cache strategies (write-through, write-behind, etc.)
- Cache loaders and decorators
- Performance monitoring
- Connection pooling
"""

import asyncio
import hashlib
import json
import logging
import pickle
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union

import redis
from redis import ConnectionPool
from redis.exceptions import ConnectionError, RedisError, TimeoutError

logger = logging.getLogger(__name__)


class CacheStrategy(Enum):
    """Cache strategy types."""

    WRITE_THROUGH = "write_through"
    WRITE_BEHIND = "write_behind"
    WRITE_AROUND = "write_around"
    CACHE_ASIDE = "cache_aside"
    READ_THROUGH = "read_through"


class SerializationType(Enum):
    """Serialization types."""

    JSON = "json"
    PICKLE = "pickle"
    MSGPACK = "msgpack"


class RedisCache:
    """Redis-based cache implementation with advanced features."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        max_connections: int = 20,
        retry_on_timeout: bool = True,
        socket_keepalive: bool = True,
        socket_keepalive_options: Optional[Dict] = None,
        health_check_interval: int = 30,
        key_prefix: str = "ncm:",
        default_ttl: int = 3600,
        serialization: SerializationType = SerializationType.JSON,
        compression: bool = False,
        strategy: CacheStrategy = CacheStrategy.CACHE_ASIDE,
    ):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.max_connections = max_connections
        self.retry_on_timeout = retry_on_timeout
        self.socket_keepalive = socket_keepalive
        self.socket_keepalive_options = socket_keepalive_options or {}
        self.health_check_interval = health_check_interval
        self.key_prefix = key_prefix
        self.default_ttl = default_ttl
        self.serialization = serialization
        self.compression = compression
        self.strategy = strategy

        # Connection pool
        self.pool: Optional[ConnectionPool] = None
        self.redis: Optional[redis.Redis] = None

        # Statistics
        self._hits = 0
        self._misses = 0
        self._sets = 0
        self._deletes = 0
        self._errors = 0

        # Health check
        self._last_health_check = 0
        self._is_healthy = True

        # Background tasks
        self._background_tasks: List[asyncio.Task] = []

        # Initialize connection
        self._initialize_connection()

    def _initialize_connection(self) -> None:
        """Initialize Redis connection pool."""
        try:
            self.pool = ConnectionPool(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                max_connections=self.max_connections,
                retry_on_timeout=self.retry_on_timeout,
                socket_keepalive=self.socket_keepalive,
                socket_keepalive_options=self.socket_keepalive_options,
                health_check_interval=self.health_check_interval,
            )

            self.redis = redis.Redis(connection_pool=self.pool)
            logger.info(f"Redis cache initialized: {self.host}:{self.port}/{self.db}")

        except Exception as e:
            logger.error(f"Failed to initialize Redis connection: {e}")
            raise

    def _serialize(self, value: Any) -> bytes:
        """Serialize value for storage."""
        try:
            if self.serialization == SerializationType.JSON:
                data = json.dumps(value, default=str).encode("utf-8")
            elif self.serialization == SerializationType.PICKLE:
                data = pickle.dumps(value)
            else:
                data = json.dumps(value, default=str).encode("utf-8")

            if self.compression:
                import gzip

                data = gzip.compress(data)

            return data

        except Exception as e:
            logger.error(f"Serialization failed: {e}")
            raise

    def _deserialize(self, data: bytes) -> Any:
        """Deserialize value from storage."""
        try:
            if self.compression:
                import gzip

                data = gzip.decompress(data)

            if self.serialization == SerializationType.JSON:
                return json.loads(data.decode("utf-8"))
            elif self.serialization == SerializationType.PICKLE:
                return pickle.loads(data)
            else:
                return json.loads(data.decode("utf-8"))

        except Exception as e:
            logger.error(f"Deserialization failed: {e}")
            raise

    def _get_key(self, key: str) -> str:
        """Get full key with prefix."""
        return f"{self.key_prefix}{key}"

    def _generate_sql_key(self, sql: str, params: Optional[Dict] = None) -> str:
        """Generate cache key for SQL query."""
        # Create hash of SQL and parameters
        content = sql
        if params:
            content += json.dumps(params, sort_keys=True)

        hash_obj = hashlib.md5(content.encode("utf-8"))
        return f"sql:{hash_obj.hexdigest()}"

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            full_key = self._get_key(key)
            data = await self.redis.get(full_key)

            if data is None:
                self._misses += 1
                logger.debug(f"Cache miss for key: {key}")
                return None

            value = self._deserialize(data)
            self._hits += 1
            logger.debug(f"Cache hit for key: {key}")
            return value

        except Exception as e:
            self._errors += 1
            logger.error(f"Cache get failed for key {key}: {e}")
            return None

    async def set(
        self, key: str, value: Any, ttl: Optional[int] = None, **kwargs
    ) -> bool:
        """Set value in cache."""
        try:
            full_key = self._get_key(key)
            data = self._serialize(value)
            ttl = ttl or self.default_ttl

            await self.redis.setex(full_key, ttl, data)
            self._sets += 1
            logger.debug(f"Cache set for key: {key} (TTL: {ttl}s)")
            return True

        except Exception as e:
            self._errors += 1
            logger.error(f"Cache set failed for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            full_key = self._get_key(key)
            result = await self.redis.delete(full_key)
            self._deletes += 1
            logger.debug(f"Cache delete for key: {key}")
            return bool(result)

        except Exception as e:
            self._errors += 1
            logger.error(f"Cache delete failed for key {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        try:
            full_key = self._get_key(key)
            result = await self.redis.exists(full_key)
            return bool(result)

        except Exception as e:
            self._errors += 1
            logger.error(f"Cache exists check failed for key {key}: {e}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """Clear keys matching pattern."""
        try:
            full_pattern = self._get_key(pattern)
            keys = await self.redis.keys(full_pattern)

            if keys:
                result = await self.redis.delete(*keys)
                logger.debug(f"Cleared {result} keys matching pattern: {pattern}")
                return result

            return 0

        except Exception as e:
            self._errors += 1
            logger.error(f"Cache clear pattern failed for pattern {pattern}: {e}")
            return 0

    async def clear_all(self) -> bool:
        """Clear all keys from cache."""
        try:
            # Clear only keys with our prefix
            pattern = f"{self.key_prefix}*"
            keys = await self.redis.keys(pattern)

            if keys:
                await self.redis.delete(*keys)
                logger.debug(f"Cleared {len(keys)} keys")

            return True

        except Exception as e:
            self._errors += 1
            logger.error(f"Cache clear all failed: {e}")
            return False

    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from cache."""
        try:
            full_keys = [self._get_key(key) for key in keys]
            data_list = await self.redis.mget(full_keys)

            result = {}
            for i, data in enumerate(data_list):
                if data is not None:
                    try:
                        value = self._deserialize(data)
                        result[keys[i]] = value
                        self._hits += 1
                    except Exception as e:
                        logger.error(f"Deserialization failed for key {keys[i]}: {e}")
                        self._misses += 1
                else:
                    self._misses += 1

            logger.debug(f"Cache get_many: {len(result)}/{len(keys)} hits")
            return result

        except Exception as e:
            self._errors += 1
            logger.error(f"Cache get_many failed: {e}")
            return {}

    async def set_many(
        self, mapping: Dict[str, Any], ttl: Optional[int] = None
    ) -> bool:
        """Set multiple values in cache."""
        try:
            ttl = ttl or self.default_ttl
            pipe = self.redis.pipeline()

            for key, value in mapping.items():
                full_key = self._get_key(key)
                data = self._serialize(value)
                pipe.setex(full_key, ttl, data)

            await pipe.execute()
            self._sets += len(mapping)
            logger.debug(f"Cache set_many: {len(mapping)} keys")
            return True

        except Exception as e:
            self._errors += 1
            logger.error(f"Cache set_many failed: {e}")
            return False

    async def health_check(self) -> bool:
        """Check cache health."""
        try:
            current_time = time.time()

            # Skip health check if recently checked
            if current_time - self._last_health_check < self.health_check_interval:
                return self._is_healthy

            # Perform health check
            await self.redis.ping()
            self._is_healthy = True
            self._last_health_check = current_time
            logger.debug("Redis health check passed")
            return True

        except Exception as e:
            self._is_healthy = False
            self._errors += 1
            logger.error(f"Redis health check failed: {e}")
            return False

    async def close(self) -> None:
        """Close cache connection."""
        try:
            if self.redis:
                await self.redis.close()
            if self.pool:
                await self.pool.disconnect()
            logger.debug("Redis cache connection closed")

        except Exception as e:
            logger.error(f"Failed to close Redis connection: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0

        return {
            "hits": self._hits,
            "misses": self._misses,
            "sets": self._sets,
            "deletes": self._deletes,
            "errors": self._errors,
            "hit_rate": hit_rate,
            "total_requests": total_requests,
            "is_healthy": self._is_healthy,
            "strategy": self.strategy.value,
            "serialization": self.serialization.value,
            "compression": self.compression,
        }

    # SQL Cache Methods
    async def cache_sql_query(
        self,
        sql: str,
        params: Optional[Dict] = None,
        ttl: Optional[int] = None,
        key_suffix: Optional[str] = None,
    ) -> Optional[Any]:
        """Cache SQL query result."""
        try:
            cache_key = self._generate_sql_key(sql, params)
            if key_suffix:
                cache_key += f":{key_suffix}"

            # Try to get from cache first
            result = await self.get(cache_key)
            if result is not None:
                logger.debug(f"SQL cache hit for query: {sql[:50]}...")
                return result

            logger.debug(f"SQL cache miss for query: {sql[:50]}...")
            return None

        except Exception as e:
            logger.error(f"SQL cache get failed: {e}")
            return None

    async def set_sql_query(
        self,
        sql: str,
        result: Any,
        params: Optional[Dict] = None,
        ttl: Optional[int] = None,
        key_suffix: Optional[str] = None,
    ) -> bool:
        """Cache SQL query result."""
        try:
            cache_key = self._generate_sql_key(sql, params)
            if key_suffix:
                cache_key += f":{key_suffix}"

            success = await self.set(cache_key, result, ttl)
            if success:
                logger.debug(f"SQL query cached: {sql[:50]}...")

            return success

        except Exception as e:
            logger.error(f"SQL cache set failed: {e}")
            return False

    async def invalidate_sql_pattern(self, pattern: str) -> int:
        """Invalidate SQL cache entries matching pattern."""
        try:
            sql_pattern = f"sql:{pattern}"
            return await self.clear_pattern(sql_pattern)

        except Exception as e:
            logger.error(f"SQL cache invalidation failed: {e}")
            return 0

    # Cache Strategy Methods
    async def write_through(
        self, key: str, value: Any, ttl: Optional[int] = None
    ) -> bool:
        """Write-through cache strategy."""
        try:
            # Write to cache first
            cache_success = await self.set(key, value, ttl)

            if cache_success:
                logger.debug(f"Write-through cache set for key: {key}")

            return cache_success

        except Exception as e:
            logger.error(f"Write-through cache failed for key {key}: {e}")
            return False

    async def write_behind(
        self, key: str, value: Any, ttl: Optional[int] = None
    ) -> bool:
        """Write-behind cache strategy."""
        try:
            # Write to cache immediately
            cache_success = await self.set(key, value, ttl)

            if cache_success:
                # Schedule background write to persistent storage
                task = asyncio.create_task(self._background_write(key, value))
                self._background_tasks.append(task)
                logger.debug(f"Write-behind cache set for key: {key}")

            return cache_success

        except Exception as e:
            logger.error(f"Write-behind cache failed for key {key}: {e}")
            return False

    async def _background_write(self, key: str, value: Any) -> None:
        """Background write for write-behind strategy."""
        try:
            # Simulate writing to persistent storage
            await asyncio.sleep(0.1)  # Simulate I/O
            logger.debug(f"Background write completed for key: {key}")

        except Exception as e:
            logger.error(f"Background write failed for key {key}: {e}")

    async def read_through(
        self, key: str, loader: Callable[[], Awaitable[Any]], ttl: Optional[int] = None
    ) -> Any:
        """Read-through cache strategy."""
        try:
            # Try to get from cache first
            value = await self.get(key)

            if value is not None:
                logger.debug(f"Read-through cache hit for key: {key}")
                return value

            # Cache miss - load from source
            logger.debug(f"Read-through cache miss for key: {key}, loading from source")
            value = await loader()

            # Store in cache
            await self.set(key, value, ttl)
            logger.debug(f"Read-through cache populated for key: {key}")

            return value

        except Exception as e:
            logger.error(f"Read-through cache failed for key {key}: {e}")
            # Fallback to loader
            return await loader()

    # Cache Loader Decorator
    def cache_loader(
        self,
        ttl: Optional[int] = None,
        key_func: Optional[Callable] = None,
        strategy: Optional[CacheStrategy] = None,
    ):
        """Cache loader decorator."""

        def decorator(func: Callable) -> Callable:
            async def wrapper(*args, **kwargs):
                # Generate cache key
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"

                # Use specified strategy or default
                cache_strategy = strategy or self.strategy

                if cache_strategy == CacheStrategy.READ_THROUGH:
                    return await self.read_through(
                        cache_key, lambda: func(*args, **kwargs), ttl
                    )
                elif cache_strategy == CacheStrategy.CACHE_ASIDE:
                    # Try cache first
                    value = await self.get(cache_key)
                    if value is not None:
                        return value

                    # Load from function
                    value = await func(*args, **kwargs)

                    # Store in cache
                    await self.set(cache_key, value, ttl)
                    return value
                else:
                    # Default behavior
                    value = await func(*args, **kwargs)
                    await self.set(cache_key, value, ttl)
                    return value

            return wrapper

        return decorator

    # TTL Management
    async def get_ttl(self, key: str) -> Optional[int]:
        """Get TTL for key."""
        try:
            full_key = self._get_key(key)
            ttl = await self.redis.ttl(full_key)
            return ttl if ttl > 0 else None

        except Exception as e:
            logger.error(f"Get TTL failed for key {key}: {e}")
            return None

    async def extend_ttl(self, key: str, ttl: int) -> bool:
        """Extend TTL for key."""
        try:
            full_key = self._get_key(key)
            result = await self.redis.expire(full_key, ttl)
            logger.debug(f"Extended TTL for key: {key} to {ttl}s")
            return bool(result)

        except Exception as e:
            logger.error(f"Extend TTL failed for key {key}: {e}")
            return False

    # Batch Operations
    async def pipeline(self):
        """Get Redis pipeline for batch operations."""
        return self.redis.pipeline()

    async def execute_pipeline(self, pipeline) -> List[Any]:
        """Execute Redis pipeline."""
        try:
            results = await pipeline.execute()
            logger.debug(f"Pipeline executed: {len(results)} operations")
            return results

        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}")
            return []

    # Cleanup
    async def cleanup_background_tasks(self) -> None:
        """Cleanup completed background tasks."""
        completed_tasks = [task for task in self._background_tasks if task.done()]
        for task in completed_tasks:
            self._background_tasks.remove(task)

        if completed_tasks:
            logger.debug(f"Cleaned up {len(completed_tasks)} background tasks")
