"""
Multi-level cache implementation for ncm-foundation.

This module provides multi-level caching functionality including:
- L1 (Memory) and L2 (Redis) cache levels
- Automatic cache promotion
- Cache stampede prevention
- Performance optimization
- Level-specific strategies
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union

from .redis_cache import CacheStrategy, RedisCache, SerializationType

logger = logging.getLogger(__name__)


class CacheLevel(Enum):
    """Cache level enumeration."""

    L1 = "l1"  # Memory cache
    L2 = "l2"  # Redis cache


class MultiLevelCache:
    """Multi-level cache implementation with L1 (memory) and L2 (Redis)."""

    def __init__(
        self,
        l2_cache: RedisCache,
        l1_max_size: int = 1000,
        l1_default_ttl: int = 300,  # 5 minutes
        l2_default_ttl: int = 3600,  # 1 hour
        enable_promotion: bool = True,
        enable_stampede_prevention: bool = True,
        promotion_threshold: int = 2,
        max_l1_ttl: int = 1800,  # 30 minutes
        compression_threshold: int = 1024,  # 1KB
    ):
        self.l2_cache = l2_cache
        self.l1_max_size = l1_max_size
        self.l1_default_ttl = l1_default_ttl
        self.l2_default_ttl = l2_default_ttl
        self.enable_promotion = enable_promotion
        self.enable_stampede_prevention = enable_stampede_prevention
        self.promotion_threshold = promotion_threshold
        self.max_l1_ttl = max_l1_ttl
        self.compression_threshold = compression_threshold

        # L1 cache (in-memory)
        self.l1_cache: Dict[str, Dict[str, Any]] = {}
        self.l1_access_count: Dict[str, int] = {}
        self.l1_last_access: Dict[str, float] = {}

        # Locks for stampede prevention
        self._locks: Dict[str, asyncio.Lock] = {}
        self._loading_keys: set = set()

        # Statistics
        self._l1_hits = 0
        self._l2_hits = 0
        self._misses = 0
        self._promotions = 0
        self._evictions = 0
        self._stampede_preventions = 0

        # Background tasks
        self._background_tasks: List[asyncio.Task] = []
        self._cleanup_task: Optional[asyncio.Task] = None

        # Start background cleanup
        self._start_background_cleanup()

    def _get_lock(self, key: str) -> asyncio.Lock:
        """Get or create lock for key to prevent cache stampede."""
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]

    def _start_background_cleanup(self) -> None:
        """Start background cleanup task."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._background_cleanup_loop())

    async def _background_cleanup_loop(self) -> None:
        """Background cleanup loop for L1 cache."""
        while True:
            try:
                await asyncio.sleep(60)  # Cleanup every minute
                await self._cleanup_l1_cache()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Background cleanup failed: {e}")

    async def _cleanup_l1_cache(self) -> None:
        """Cleanup expired entries from L1 cache."""
        try:
            current_time = time.time()
            expired_keys = []

            for key, cache_data in self.l1_cache.items():
                if current_time > cache_data.get("expires_at", 0):
                    expired_keys.append(key)

            # Remove expired keys
            for key in expired_keys:
                await self._remove_from_l1(key)

            # Evict least recently used if over capacity
            if len(self.l1_cache) > self.l1_max_size:
                await self._evict_lru_entries()

            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired L1 entries")

        except Exception as e:
            logger.error(f"L1 cache cleanup failed: {e}")

    async def _evict_lru_entries(self) -> None:
        """Evict least recently used entries from L1 cache."""
        try:
            # Sort by last access time
            sorted_keys = sorted(
                self.l1_cache.keys(), key=lambda k: self.l1_last_access.get(k, 0)
            )

            # Remove oldest entries
            to_remove = len(self.l1_cache) - self.l1_max_size
            for key in sorted_keys[:to_remove]:
                await self._remove_from_l1(key)
                self._evictions += 1

            logger.debug(f"Evicted {to_remove} LRU entries from L1 cache")

        except Exception as e:
            logger.error(f"LRU eviction failed: {e}")

    async def _remove_from_l1(self, key: str) -> None:
        """Remove key from L1 cache."""
        if key in self.l1_cache:
            del self.l1_cache[key]
        if key in self.l1_access_count:
            del self.l1_access_count[key]
        if key in self.l1_last_access:
            del self.l1_last_access[key]

    async def _store_in_l1(
        self, key: str, value: Any, ttl: Optional[int] = None
    ) -> None:
        """Store value in L1 cache."""
        try:
            ttl = min(ttl or self.l1_default_ttl, self.max_l1_ttl)
            expires_at = time.time() + ttl

            # Compress large values
            if (
                self.compression_threshold > 0
                and len(str(value)) > self.compression_threshold
            ):
                import gzip
                import json

                compressed_data = gzip.compress(json.dumps(value).encode())
                cache_data = {
                    "value": compressed_data,
                    "compressed": True,
                    "expires_at": expires_at,
                    "created_at": time.time(),
                }
            else:
                cache_data = {
                    "value": value,
                    "compressed": False,
                    "expires_at": expires_at,
                    "created_at": time.time(),
                }

            self.l1_cache[key] = cache_data
            self.l1_last_access[key] = time.time()

            # Evict if over capacity
            if len(self.l1_cache) > self.l1_max_size:
                await self._evict_lru_entries()

        except Exception as e:
            logger.error(f"Failed to store in L1 cache: {e}")

    async def _get_from_l1(self, key: str) -> Optional[Any]:
        """Get value from L1 cache."""
        try:
            if key not in self.l1_cache:
                return None

            cache_data = self.l1_cache[key]
            current_time = time.time()

            # Check expiration
            if current_time > cache_data.get("expires_at", 0):
                await self._remove_from_l1(key)
                return None

            # Update access tracking
            self.l1_last_access[key] = current_time
            self.l1_access_count[key] = self.l1_access_count.get(key, 0) + 1

            # Check promotion threshold
            if (
                self.enable_promotion
                and self.l1_access_count[key] >= self.promotion_threshold
            ):
                await self._promote_to_l2(key, cache_data["value"])

            # Decompress if needed
            value = cache_data["value"]
            if cache_data.get("compressed", False):
                import gzip
                import json

                value = json.loads(gzip.decompress(value).decode())

            return value

        except Exception as e:
            logger.error(f"Failed to get from L1 cache: {e}")
            return None

    async def _promote_to_l2(self, key: str, value: Any) -> None:
        """Promote frequently accessed L1 entries to L2."""
        try:
            await self.l2_cache.set(key, value, self.l2_default_ttl)
            self._promotions += 1
            logger.debug(f"Promoted key {key} to L2 cache")

        except Exception as e:
            logger.error(f"Failed to promote key {key} to L2: {e}")

    async def get(
        self,
        key: str,
        loader: Optional[Callable[[], Awaitable[Any]]] = None,
        ttl: Optional[int] = None,
    ) -> Optional[Any]:
        """Get value from multi-level cache."""
        try:
            # Try L1 cache first
            value = await self._get_from_l1(key)
            if value is not None:
                self._l1_hits += 1
                logger.debug(f"L1 cache hit for key: {key}")
                return value

            # Try L2 cache
            value = await self.l2_cache.get(key)
            if value is not None:
                self._l2_hits += 1
                logger.debug(f"L2 cache hit for key: {key}")

                # Promote to L1
                await self._store_in_l1(key, value, ttl)
                return value

            # Cache miss - use loader if provided
            if loader is not None:
                if self.enable_stampede_prevention and key in self._loading_keys:
                    # Wait for ongoing load
                    async with self._get_lock(key):
                        # Check again after acquiring lock
                        value = await self._get_from_l1(key)
                        if value is not None:
                            return value

                        value = await self.l2_cache.get(key)
                        if value is not None:
                            await self._store_in_l1(key, value, ttl)
                            return value

                # Load from source
                if self.enable_stampede_prevention:
                    self._loading_keys.add(key)

                try:
                    value = await loader()

                    # Store in both levels
                    await self._store_in_l1(key, value, ttl)
                    await self.l2_cache.set(key, value, self.l2_default_ttl)

                    self._misses += 1
                    logger.debug(f"Loaded from source for key: {key}")
                    return value

                finally:
                    if self.enable_stampede_prevention:
                        self._loading_keys.discard(key)

            # No loader provided
            self._misses += 1
            logger.debug(f"Cache miss for key: {key}")
            return None

        except Exception as e:
            logger.error(f"Multi-level cache get failed for key {key}: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        level: Optional[CacheLevel] = None,
        **kwargs,
    ) -> bool:
        """Set value in multi-level cache."""
        try:
            if level == CacheLevel.L1:
                # Store only in L1
                await self._store_in_l1(key, value, ttl)
                logger.debug(f"L1 cache set for key: {key}")
                return True
            elif level == CacheLevel.L2:
                # Store only in L2
                success = await self.l2_cache.set(
                    key, value, ttl or self.l2_default_ttl
                )
                logger.debug(f"L2 cache set for key: {key}")
                return success
            else:
                # Store in both levels
                l1_success = await self._store_in_l1(key, value, ttl)
                l2_success = await self.l2_cache.set(
                    key, value, ttl or self.l2_default_ttl
                )

                success = l1_success and l2_success
                if success:
                    logger.debug(f"Multi-level cache set for key: {key}")
                else:
                    logger.warning(f"Multi-level cache set failed for key: {key}")

                return success

        except Exception as e:
            logger.error(f"Multi-level cache set failed for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from multi-level cache."""
        try:
            # Remove from both levels
            l1_success = True
            if key in self.l1_cache:
                await self._remove_from_l1(key)

            l2_success = await self.l2_cache.delete(key)

            success = l1_success and l2_success
            if success:
                logger.debug(f"Multi-level cache delete for key: {key}")
            else:
                logger.warning(f"Multi-level cache delete failed for key: {key}")

            return success

        except Exception as e:
            logger.error(f"Multi-level cache delete failed for key {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in multi-level cache."""
        try:
            # Check L1 first
            if key in self.l1_cache:
                cache_data = self.l1_cache[key]
                if time.time() <= cache_data.get("expires_at", 0):
                    return True
                else:
                    await self._remove_from_l1(key)

            # Check L2
            return await self.l2_cache.exists(key)

        except Exception as e:
            logger.error(f"Multi-level cache exists check failed for key {key}: {e}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """Clear keys matching pattern from both levels."""
        try:
            # Clear from L1 (exact match only for patterns)
            l1_count = 0
            if "*" in pattern:
                # Pattern matching for L1
                import fnmatch

                keys_to_remove = [
                    k for k in self.l1_cache.keys() if fnmatch.fnmatch(k, pattern)
                ]
                for key in keys_to_remove:
                    await self._remove_from_l1(key)
                    l1_count += 1
            else:
                # Exact match
                if pattern in self.l1_cache:
                    await self._remove_from_l1(pattern)
                    l1_count = 1

            # Clear from L2
            l2_count = await self.l2_cache.clear_pattern(pattern)

            total_count = l1_count + l2_count
            logger.debug(f"Cleared {total_count} keys matching pattern: {pattern}")
            return total_count

        except Exception as e:
            logger.error(
                f"Multi-level cache clear pattern failed for pattern {pattern}: {e}"
            )
            return 0

    async def clear_all(self) -> bool:
        """Clear all keys from both levels."""
        try:
            # Clear L1
            self.l1_cache.clear()
            self.l1_access_count.clear()
            self.l1_last_access.clear()

            # Clear L2
            l2_success = await self.l2_cache.clear_all()

            success = l2_success
            if success:
                logger.debug("Cleared all multi-level cache keys")
            else:
                logger.warning("Multi-level cache clear all failed")

            return success

        except Exception as e:
            logger.error(f"Multi-level cache clear all failed: {e}")
            return False

    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from multi-level cache."""
        try:
            result = {}
            remaining_keys = keys.copy()

            # Try L1 cache first
            for key in keys:
                value = await self._get_from_l1(key)
                if value is not None:
                    result[key] = value
                    remaining_keys.remove(key)

            if remaining_keys:
                # Try L2 cache for remaining keys
                l2_results = await self.l2_cache.get_many(remaining_keys)
                result.update(l2_results)

                # Promote L2 results to L1
                for key, value in l2_results.items():
                    await self._store_in_l1(key, value)

            logger.debug(f"Multi-level cache get_many: {len(result)}/{len(keys)} hits")
            return result

        except Exception as e:
            logger.error(f"Multi-level cache get_many failed: {e}")
            return {}

    async def set_many(
        self, mapping: Dict[str, Any], ttl: Optional[int] = None
    ) -> bool:
        """Set multiple values in multi-level cache."""
        try:
            # Set in L1
            for key, value in mapping.items():
                await self._store_in_l1(key, value, ttl)

            # Set in L2
            l2_success = await self.l2_cache.set_many(
                mapping, ttl or self.l2_default_ttl
            )

            success = l2_success
            if success:
                logger.debug(f"Multi-level cache set_many: {len(mapping)} keys")
            else:
                logger.warning(
                    f"Multi-level cache set_many failed: {len(mapping)} keys"
                )

            return success

        except Exception as e:
            logger.error(f"Multi-level cache set_many failed: {e}")
            return False

    async def health_check(self) -> bool:
        """Check health of both cache levels."""
        try:
            # Check L1 cache health
            l1_health = len(self.l1_cache) >= 0  # Basic check

            # Check L2 cache health
            l2_health = await self.l2_cache.health_check()

            health = l1_health and l2_health
            if not health:
                logger.warning(
                    f"Multi-level cache health check failed - L1: {l1_health}, L2: {l2_health}"
                )

            return health

        except Exception as e:
            logger.error(f"Multi-level cache health check failed: {e}")
            return False

    async def close(self) -> None:
        """Close multi-level cache."""
        try:
            # Cancel background tasks
            if self._cleanup_task and not self._cleanup_task.done():
                self._cleanup_task.cancel()
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass

            # Cancel other background tasks
            for task in self._background_tasks:
                if not task.done():
                    task.cancel()

            if self._background_tasks:
                await asyncio.gather(*self._background_tasks, return_exceptions=True)

            # Close L2 cache
            await self.l2_cache.close()

            # Clear L1 cache
            self.l1_cache.clear()
            self.l1_access_count.clear()
            self.l1_last_access.clear()

            logger.debug("Multi-level cache closed")

        except Exception as e:
            logger.error(f"Failed to close multi-level cache: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get multi-level cache statistics."""
        total_requests = self._l1_hits + self._l2_hits + self._misses
        l1_hit_rate = self._l1_hits / total_requests if total_requests > 0 else 0
        l2_hit_rate = self._l2_hits / total_requests if total_requests > 0 else 0
        overall_hit_rate = (
            (self._l1_hits + self._l2_hits) / total_requests
            if total_requests > 0
            else 0
        )

        return {
            "l1_stats": {
                "size": len(self.l1_cache),
                "max_size": self.l1_max_size,
                "hits": self._l1_hits,
                "hit_rate": l1_hit_rate,
                "promotions": self._promotions,
                "evictions": self._evictions,
            },
            "l2_stats": self.l2_cache.get_stats(),
            "overall_stats": {
                "l1_hits": self._l1_hits,
                "l2_hits": self._l2_hits,
                "misses": self._misses,
                "overall_hit_rate": overall_hit_rate,
                "total_requests": total_requests,
                "stampede_preventions": self._stampede_preventions,
            },
            "configuration": {
                "l1_max_size": self.l1_max_size,
                "l1_default_ttl": self.l1_default_ttl,
                "l2_default_ttl": self.l2_default_ttl,
                "enable_promotion": self.enable_promotion,
                "enable_stampede_prevention": self.enable_stampede_prevention,
                "promotion_threshold": self.promotion_threshold,
                "max_l1_ttl": self.max_l1_ttl,
                "compression_threshold": self.compression_threshold,
            },
        }

    # Cache Loader Decorator
    def cache_loader(
        self,
        ttl: Optional[int] = None,
        level: Optional[CacheLevel] = None,
        key_func: Optional[Callable] = None,
    ):
        """Multi-level cache loader decorator."""

        def decorator(func: Callable) -> Callable:
            async def wrapper(*args, **kwargs):
                # Generate cache key
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"

                # Try to get from cache
                value = await self.get(cache_key, ttl=ttl)
                if value is not None:
                    return value

                # Load from function
                value = await func(*args, **kwargs)

                # Store in cache
                await self.set(cache_key, value, ttl, level)
                return value

            return wrapper

        return decorator
