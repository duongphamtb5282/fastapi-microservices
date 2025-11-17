"""
Cache strategies implementation for ncm-foundation.

This module provides various cache strategies including:
- Write-through
- Write-behind
- Write-around
- Cache-aside
- Read-through
- Cache warming
- Cache invalidation strategies
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union

from .redis_cache import CacheStrategy, RedisCache

logger = logging.getLogger(__name__)


class InvalidationStrategy(Enum):
    """Cache invalidation strategies."""

    TIME_BASED = "time_based"
    EVENT_BASED = "event_based"
    PATTERN_BASED = "pattern_based"
    DEPENDENCY_BASED = "dependency_based"
    MANUAL = "manual"


class CacheStrategies:
    """Cache strategies implementation."""

    def __init__(self, redis_cache: RedisCache):
        self.redis_cache = redis_cache
        self._background_tasks: List[asyncio.Task] = []
        self._invalidation_callbacks: Dict[str, List[Callable]] = {}
        self._dependency_graph: Dict[str, List[str]] = {}

        # Strategy metrics
        self._write_through_count = 0
        self._write_behind_count = 0
        self._write_around_count = 0
        self._cache_aside_count = 0
        self._read_through_count = 0

        # Invalidation metrics
        self._time_based_invalidations = 0
        self._event_based_invalidations = 0
        self._pattern_based_invalidations = 0
        self._dependency_based_invalidations = 0

    # Write Strategies

    async def write_through(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        persistent_store: Optional[Callable] = None,
    ) -> bool:
        """Write-through cache strategy."""
        try:
            # Write to cache
            cache_success = await self.redis_cache.set(key, value, ttl)

            if cache_success and persistent_store:
                # Write to persistent storage
                await persistent_store(key, value)

            self._write_through_count += 1
            logger.debug(f"Write-through cache set for key: {key}")
            return cache_success

        except Exception as e:
            logger.error(f"Write-through cache failed for key {key}: {e}")
            return False

    async def write_behind(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        persistent_store: Optional[Callable] = None,
        delay: float = 0.0,
    ) -> bool:
        """Write-behind cache strategy."""
        try:
            # Write to cache immediately
            cache_success = await self.redis_cache.set(key, value, ttl)

            if cache_success and persistent_store:
                # Schedule background write to persistent storage
                task = asyncio.create_task(
                    self._background_persistent_write(
                        key, value, persistent_store, delay
                    )
                )
                self._background_tasks.append(task)

            self._write_behind_count += 1
            logger.debug(f"Write-behind cache set for key: {key}")
            return cache_success

        except Exception as e:
            logger.error(f"Write-behind cache failed for key {key}: {e}")
            return False

    async def write_around(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        persistent_store: Optional[Callable] = None,
    ) -> bool:
        """Write-around cache strategy."""
        try:
            # Write to persistent storage first
            if persistent_store:
                await persistent_store(key, value)

            # Don't write to cache (write-around)
            self._write_around_count += 1
            logger.debug(f"Write-around cache set for key: {key}")
            return True

        except Exception as e:
            logger.error(f"Write-around cache failed for key {key}: {e}")
            return False

    async def cache_aside(
        self, key: str, value: Any, ttl: Optional[int] = None
    ) -> bool:
        """Cache-aside strategy."""
        try:
            # Write to cache only
            cache_success = await self.redis_cache.set(key, value, ttl)

            self._cache_aside_count += 1
            logger.debug(f"Cache-aside cache set for key: {key}")
            return cache_success

        except Exception as e:
            logger.error(f"Cache-aside cache failed for key {key}: {e}")
            return False

    async def read_through(
        self, key: str, loader: Callable[[], Awaitable[Any]], ttl: Optional[int] = None
    ) -> Any:
        """Read-through cache strategy."""
        try:
            # Try cache first
            value = await self.redis_cache.get(key)

            if value is not None:
                self._read_through_count += 1
                logger.debug(f"Read-through cache hit for key: {key}")
                return value

            # Cache miss - load from source
            logger.debug(f"Read-through cache miss for key: {key}, loading from source")
            value = await loader()

            # Store in cache
            await self.redis_cache.set(key, value, ttl)
            self._read_through_count += 1
            logger.debug(f"Read-through cache populated for key: {key}")

            return value

        except Exception as e:
            logger.error(f"Read-through cache failed for key {key}: {e}")
            # Fallback to loader
            return await loader()

    async def _background_persistent_write(
        self, key: str, value: Any, persistent_store: Callable, delay: float
    ) -> None:
        """Background persistent write for write-behind strategy."""
        try:
            if delay > 0:
                await asyncio.sleep(delay)

            await persistent_store(key, value)
            logger.debug(f"Background persistent write completed for key: {key}")

        except Exception as e:
            logger.error(f"Background persistent write failed for key {key}: {e}")

    # Invalidation Strategies

    async def time_based_invalidation(
        self, key: str, ttl: int, callback: Optional[Callable] = None
    ) -> bool:
        """Time-based cache invalidation."""
        try:
            # Set TTL for automatic expiration
            success = await self.redis_cache.set(
                key, await self.redis_cache.get(key), ttl
            )

            if success and callback:
                # Schedule callback for when TTL expires
                task = asyncio.create_task(
                    self._schedule_ttl_callback(key, ttl, callback)
                )
                self._background_tasks.append(task)

            self._time_based_invalidations += 1
            logger.debug(f"Time-based invalidation set for key: {key} (TTL: {ttl}s)")
            return success

        except Exception as e:
            logger.error(f"Time-based invalidation failed for key {key}: {e}")
            return False

    async def event_based_invalidation(
        self, event_name: str, keys: List[str], callback: Optional[Callable] = None
    ) -> bool:
        """Event-based cache invalidation."""
        try:
            # Register invalidation callback for event
            if event_name not in self._invalidation_callbacks:
                self._invalidation_callbacks[event_name] = []

            self._invalidation_callbacks[event_name].append(
                {"keys": keys, "callback": callback}
            )

            self._event_based_invalidations += 1
            logger.debug(f"Event-based invalidation registered for event: {event_name}")
            return True

        except Exception as e:
            logger.error(f"Event-based invalidation failed for event {event_name}: {e}")
            return False

    async def trigger_event_invalidation(self, event_name: str) -> int:
        """Trigger event-based invalidation."""
        try:
            if event_name not in self._invalidation_callbacks:
                return 0

            total_invalidated = 0
            for callback_data in self._invalidation_callbacks[event_name]:
                keys = callback_data["keys"]
                callback = callback_data["callback"]

                # Invalidate keys
                for key in keys:
                    await self.redis_cache.delete(key)
                    total_invalidated += 1

                # Execute callback if provided
                if callback:
                    await callback(event_name, keys)

            logger.debug(
                f"Event-based invalidation triggered for event: {event_name} ({total_invalidated} keys)"
            )
            return total_invalidated

        except Exception as e:
            logger.error(
                f"Event-based invalidation trigger failed for event {event_name}: {e}"
            )
            return 0

    async def pattern_based_invalidation(
        self, pattern: str, callback: Optional[Callable] = None
    ) -> int:
        """Pattern-based cache invalidation."""
        try:
            # Find and invalidate keys matching pattern
            count = await self.redis_cache.clear_pattern(pattern)

            if callback:
                await callback(pattern, count)

            self._pattern_based_invalidations += 1
            logger.debug(
                f"Pattern-based invalidation: {count} keys matching pattern: {pattern}"
            )
            return count

        except Exception as e:
            logger.error(
                f"Pattern-based invalidation failed for pattern {pattern}: {e}"
            )
            return 0

    async def dependency_based_invalidation(
        self, key: str, dependencies: List[str], callback: Optional[Callable] = None
    ) -> bool:
        """Dependency-based cache invalidation."""
        try:
            # Register dependencies
            self._dependency_graph[key] = dependencies

            # Set up invalidation for dependencies
            for dep_key in dependencies:
                await self.event_based_invalidation(f"invalidate_{dep_key}", [key])

            if callback:
                # Register callback for dependency invalidation
                await self.event_based_invalidation(f"callback_{key}", [key], callback)

            self._dependency_based_invalidations += 1
            logger.debug(f"Dependency-based invalidation set for key: {key}")
            return True

        except Exception as e:
            logger.error(f"Dependency-based invalidation failed for key {key}: {e}")
            return False

    async def invalidate_dependencies(self, key: str) -> int:
        """Invalidate all keys that depend on the given key."""
        try:
            # Find keys that depend on this key
            dependent_keys = []
            for dependent_key, dependencies in self._dependency_graph.items():
                if key in dependencies:
                    dependent_keys.append(dependent_key)

            # Invalidate dependent keys
            total_invalidated = 0
            for dep_key in dependent_keys:
                await self.redis_cache.delete(dep_key)
                total_invalidated += 1

            logger.debug(
                f"Dependency invalidation: {total_invalidated} keys invalidated for dependency: {key}"
            )
            return total_invalidated

        except Exception as e:
            logger.error(f"Dependency invalidation failed for key {key}: {e}")
            return 0

    async def _schedule_ttl_callback(
        self, key: str, ttl: int, callback: Callable
    ) -> None:
        """Schedule callback for TTL expiration."""
        try:
            await asyncio.sleep(ttl)

            # Check if key still exists (might have been manually deleted)
            if await self.redis_cache.exists(key):
                await callback(key, "ttl_expired")

        except Exception as e:
            logger.error(f"TTL callback failed for key {key}: {e}")

    # Cache Warming Strategies

    async def warm_cache(
        self,
        warming_data: List[Dict[str, Any]],
        strategy: CacheStrategy = CacheStrategy.CACHE_ASIDE,
        concurrency: int = 5,
    ) -> Dict[str, Any]:
        """Warm cache with predefined data."""
        try:
            results = {
                "total_items": len(warming_data),
                "successful": 0,
                "failed": 0,
                "errors": [],
            }

            # Process items in batches
            semaphore = asyncio.Semaphore(concurrency)

            async def process_item(item_data: Dict[str, Any]) -> None:
                async with semaphore:
                    try:
                        key = item_data["key"]
                        value = item_data["value"]
                        ttl = item_data.get("ttl")

                        if strategy == CacheStrategy.WRITE_THROUGH:
                            success = await self.write_through(key, value, ttl)
                        elif strategy == CacheStrategy.WRITE_BEHIND:
                            success = await self.write_behind(key, value, ttl)
                        elif strategy == CacheStrategy.WRITE_AROUND:
                            success = await self.write_around(key, value, ttl)
                        else:
                            success = await self.cache_aside(key, value, ttl)

                        if success:
                            results["successful"] += 1
                        else:
                            results["failed"] += 1

                    except Exception as e:
                        results["failed"] += 1
                        results["errors"].append(str(e))
                        logger.error(f"Cache warming failed for item: {e}")

            # Execute all items
            tasks = [process_item(item) for item in warming_data]
            await asyncio.gather(*tasks, return_exceptions=True)

            logger.info(
                f"Cache warming completed: {results['successful']}/{results['total_items']} successful"
            )
            return results

        except Exception as e:
            logger.error(f"Cache warming failed: {e}")
            return {"error": str(e)}

    # Cache Loader Decorators

    def cache_loader(
        self,
        ttl: Optional[int] = None,
        strategy: CacheStrategy = CacheStrategy.CACHE_ASIDE,
        key_func: Optional[Callable] = None,
        invalidation_strategy: Optional[InvalidationStrategy] = None,
        invalidation_params: Optional[Dict] = None,
    ):
        """Cache loader decorator with strategy support."""

        def decorator(func: Callable) -> Callable:
            async def wrapper(*args, **kwargs):
                # Generate cache key
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"

                # Apply strategy
                if strategy == CacheStrategy.READ_THROUGH:
                    return await self.read_through(
                        cache_key, lambda: func(*args, **kwargs), ttl
                    )
                elif strategy == CacheStrategy.CACHE_ASIDE:
                    # Try cache first
                    value = await self.redis_cache.get(cache_key)
                    if value is not None:
                        return value

                    # Execute function and cache result
                    value = await func(*args, **kwargs)
                    await self.cache_aside(cache_key, value, ttl)
                    return value
                else:
                    # Default behavior
                    value = await func(*args, **kwargs)
                    await self.cache_aside(cache_key, value, ttl)
                    return value

            return wrapper

        return decorator

    # Statistics and Monitoring

    def get_strategy_stats(self) -> Dict[str, Any]:
        """Get cache strategy statistics."""
        return {
            "write_through_count": self._write_through_count,
            "write_behind_count": self._write_behind_count,
            "write_around_count": self._write_around_count,
            "cache_aside_count": self._cache_aside_count,
            "read_through_count": self._read_through_count,
            "time_based_invalidations": self._time_based_invalidations,
            "event_based_invalidations": self._event_based_invalidations,
            "pattern_based_invalidations": self._pattern_based_invalidations,
            "dependency_based_invalidations": self._dependency_based_invalidations,
            "registered_callbacks": len(self._invalidation_callbacks),
            "dependency_graph_size": len(self._dependency_graph),
            "background_tasks": len(self._background_tasks),
        }

    async def cleanup_background_tasks(self) -> None:
        """Cleanup completed background tasks."""
        completed_tasks = [task for task in self._background_tasks if task.done()]
        for task in completed_tasks:
            self._background_tasks.remove(task)

        if completed_tasks:
            logger.debug(f"Cleaned up {len(completed_tasks)} background tasks")

    async def close(self) -> None:
        """Close cache strategies and cleanup resources."""
        try:
            # Cancel all background tasks
            for task in self._background_tasks:
                if not task.done():
                    task.cancel()

            # Wait for tasks to complete
            if self._background_tasks:
                await asyncio.gather(*self._background_tasks, return_exceptions=True)

            logger.debug("Cache strategies closed")

        except Exception as e:
            logger.error(f"Failed to close cache strategies: {e}")
