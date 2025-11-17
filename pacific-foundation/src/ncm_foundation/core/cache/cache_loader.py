"""
Cache loader implementation for ncm-foundation.

This module provides cache loader functionality including:
- Automatic cache loading
- Cache warming
- Cache invalidation
- Performance monitoring
- Decorator-based caching
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union

from .redis_cache import CacheStrategy, RedisCache, SerializationType

logger = logging.getLogger(__name__)


class CacheLoader:
    """Cache loader implementation with advanced features."""

    def __init__(
        self,
        redis_cache: RedisCache,
        default_ttl: int = 3600,
        enable_metrics: bool = True,
        enable_logging: bool = True,
    ):
        self.redis_cache = redis_cache
        self.default_ttl = default_ttl
        self.enable_metrics = enable_metrics
        self.enable_logging = enable_logging

        # Metrics
        self._load_hits = 0
        self._load_misses = 0
        self._load_errors = 0
        self._total_load_time = 0.0
        self._cache_hit_time = 0.0
        self._loader_time = 0.0

        # Loader registry
        self._loaders: Dict[str, Callable] = {}
        self._loader_metadata: Dict[str, Dict[str, Any]] = {}

        # Cache warming
        self._warming_tasks: List[asyncio.Task] = []

    def register_loader(
        self,
        name: str,
        loader_func: Callable,
        ttl: Optional[int] = None,
        strategy: CacheStrategy = CacheStrategy.CACHE_ASIDE,
        key_generator: Optional[Callable] = None,
        invalidation_keys: Optional[List[str]] = None,
    ) -> None:
        """Register a cache loader."""
        self._loaders[name] = loader_func
        self._loader_metadata[name] = {
            "ttl": ttl or self.default_ttl,
            "strategy": strategy,
            "key_generator": key_generator,
            "invalidation_keys": invalidation_keys or [],
            "created_at": datetime.utcnow().isoformat(),
            "load_count": 0,
            "hit_count": 0,
            "miss_count": 0,
        }

        logger.debug(f"Registered cache loader: {name}")

    async def load(self, name: str, *args, **kwargs) -> Any:
        """Load data using registered loader."""
        start_time = time.time()

        try:
            if name not in self._loaders:
                raise ValueError(f"Unknown loader: {name}")

            loader_func = self._loaders[name]
            metadata = self._loader_metadata[name]

            # Generate cache key
            if metadata["key_generator"]:
                cache_key = metadata["key_generator"](*args, **kwargs)
            else:
                cache_key = f"{name}:{hash(str(args) + str(kwargs))}"

            # Apply strategy
            if metadata["strategy"] == CacheStrategy.READ_THROUGH:
                result = await self._read_through_load(
                    cache_key, loader_func, *args, **kwargs
                )
            elif metadata["strategy"] == CacheStrategy.CACHE_ASIDE:
                result = await self._cache_aside_load(
                    cache_key, loader_func, *args, **kwargs
                )
            else:
                result = await self._default_load(
                    cache_key, loader_func, *args, **kwargs
                )

            # Update metrics
            metadata["load_count"] += 1
            execution_time = time.time() - start_time
            self._total_load_time += execution_time

            if self.enable_logging:
                logger.debug(f"Cache loader '{name}' executed in {execution_time:.3f}s")

            return result

        except Exception as e:
            self._load_errors += 1
            execution_time = time.time() - start_time
            logger.error(f"Cache loader '{name}' failed: {e}")
            raise

    async def _read_through_load(
        self, cache_key: str, loader_func: Callable, *args, **kwargs
    ) -> Any:
        """Read-through cache loading."""
        # Try cache first
        cache_start = time.time()
        value = await self.redis_cache.get(cache_key)
        cache_time = time.time() - cache_start

        if value is not None:
            self._load_hits += 1
            self._cache_hit_time += cache_time
            return value

        # Cache miss - load from source
        loader_start = time.time()
        value = await loader_func(*args, **kwargs)
        loader_time = time.time() - loader_start

        # Store in cache
        await self.redis_cache.set(cache_key, value, self.default_ttl)

        self._load_misses += 1
        self._loader_time += loader_time
        return value

    async def _cache_aside_load(
        self, cache_key: str, loader_func: Callable, *args, **kwargs
    ) -> Any:
        """Cache-aside loading."""
        # Try cache first
        cache_start = time.time()
        value = await self.redis_cache.get(cache_key)
        cache_time = time.time() - cache_start

        if value is not None:
            self._load_hits += 1
            self._cache_hit_time += cache_time
            return value

        # Cache miss - load from source
        loader_start = time.time()
        value = await loader_func(*args, **kwargs)
        loader_time = time.time() - loader_start

        # Store in cache
        await self.redis_cache.set(cache_key, value, self.default_ttl)

        self._load_misses += 1
        self._loader_time += loader_time
        return value

    async def _default_load(
        self, cache_key: str, loader_func: Callable, *args, **kwargs
    ) -> Any:
        """Default loading behavior."""
        # Load from source
        loader_start = time.time()
        value = await loader_func(*args, **kwargs)
        loader_time = time.time() - loader_start

        # Store in cache
        await self.redis_cache.set(cache_key, value, self.default_ttl)

        self._load_misses += 1
        self._loader_time += loader_time
        return value

    async def warm_cache(
        self, warming_config: List[Dict[str, Any]], concurrency: int = 5
    ) -> Dict[str, Any]:
        """Warm cache with predefined data."""
        try:
            results = {
                "total_items": len(warming_config),
                "successful": 0,
                "failed": 0,
                "errors": [],
            }

            # Process items in batches
            semaphore = asyncio.Semaphore(concurrency)

            async def process_item(item_config: Dict[str, Any]) -> None:
                async with semaphore:
                    try:
                        name = item_config["name"]
                        args = item_config.get("args", [])
                        kwargs = item_config.get("kwargs", {})

                        await self.load(name, *args, **kwargs)
                        results["successful"] += 1

                    except Exception as e:
                        results["failed"] += 1
                        results["errors"].append(str(e))
                        logger.error(f"Cache warming failed for item: {e}")

            # Execute all items
            tasks = [process_item(item) for item in warming_config]
            await asyncio.gather(*tasks, return_exceptions=True)

            logger.info(
                f"Cache warming completed: {results['successful']}/{results['total_items']} successful"
            )
            return results

        except Exception as e:
            logger.error(f"Cache warming failed: {e}")
            return {"error": str(e)}

    async def invalidate_loader(self, name: str) -> int:
        """Invalidate cache for a specific loader."""
        try:
            if name not in self._loader_metadata:
                return 0

            metadata = self._loader_metadata[name]
            invalidation_keys = metadata["invalidation_keys"]

            total_invalidated = 0
            for key in invalidation_keys:
                success = await self.redis_cache.delete(key)
                if success:
                    total_invalidated += 1

            logger.debug(f"Invalidated {total_invalidated} keys for loader: {name}")
            return total_invalidated

        except Exception as e:
            logger.error(f"Loader invalidation failed for {name}: {e}")
            return 0

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate cache entries matching pattern."""
        try:
            count = await self.redis_cache.clear_pattern(pattern)
            logger.debug(f"Invalidated {count} keys matching pattern: {pattern}")
            return count

        except Exception as e:
            logger.error(f"Pattern invalidation failed for pattern {pattern}: {e}")
            return 0

    def get_loader_stats(self, name: Optional[str] = None) -> Dict[str, Any]:
        """Get loader statistics."""
        if name:
            if name not in self._loader_metadata:
                return {"error": f"Unknown loader: {name}"}

            metadata = self._loader_metadata[name]
            return {
                "name": name,
                "load_count": metadata["load_count"],
                "hit_count": metadata["hit_count"],
                "miss_count": metadata["miss_count"],
                "hit_rate": (
                    metadata["hit_count"] / metadata["load_count"]
                    if metadata["load_count"] > 0
                    else 0
                ),
                "created_at": metadata["created_at"],
                "strategy": metadata["strategy"].value,
                "ttl": metadata["ttl"],
            }

        # Return all loader stats
        total_loads = sum(meta["load_count"] for meta in self._loader_metadata.values())
        total_hits = sum(meta["hit_count"] for meta in self._loader_metadata.values())
        total_misses = sum(
            meta["miss_count"] for meta in self._loader_metadata.values()
        )

        return {
            "total_loaders": len(self._loaders),
            "total_loads": total_loads,
            "total_hits": total_hits,
            "total_misses": total_misses,
            "overall_hit_rate": total_hits / total_loads if total_loads > 0 else 0,
            "load_hits": self._load_hits,
            "load_misses": self._load_misses,
            "load_errors": self._load_errors,
            "avg_load_time": (
                self._total_load_time / total_loads if total_loads > 0 else 0
            ),
            "avg_cache_hit_time": (
                self._cache_hit_time / self._load_hits if self._load_hits > 0 else 0
            ),
            "avg_loader_time": (
                self._loader_time / self._load_misses if self._load_misses > 0 else 0
            ),
        }

    # Decorator-based caching

    def cache_loader(
        self,
        ttl: Optional[int] = None,
        strategy: CacheStrategy = CacheStrategy.CACHE_ASIDE,
        key_func: Optional[Callable] = None,
        invalidate_on: Optional[List[str]] = None,
    ):
        """Cache loader decorator."""

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Generate cache key
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"

                # Apply strategy
                if strategy == CacheStrategy.READ_THROUGH:
                    return await self._read_through_load(
                        cache_key, func, *args, **kwargs
                    )
                elif strategy == CacheStrategy.CACHE_ASIDE:
                    return await self._cache_aside_load(
                        cache_key, func, *args, **kwargs
                    )
                else:
                    return await self._default_load(cache_key, func, *args, **kwargs)

            return wrapper

        return decorator

    def cache_method(
        self,
        ttl: Optional[int] = None,
        strategy: CacheStrategy = CacheStrategy.CACHE_ASIDE,
        key_func: Optional[Callable] = None,
    ):
        """Cache method decorator for class methods."""

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(self, *args, **kwargs):
                # Generate cache key including class name
                if key_func:
                    cache_key = key_func(self, *args, **kwargs)
                else:
                    cache_key = f"{self.__class__.__name__}:{func.__name__}:{hash(str(args) + str(kwargs))}"

                # Apply strategy
                if strategy == CacheStrategy.READ_THROUGH:
                    return await self._read_through_load(
                        cache_key, func, self, *args, **kwargs
                    )
                elif strategy == CacheStrategy.CACHE_ASIDE:
                    return await self._cache_aside_load(
                        cache_key, func, self, *args, **kwargs
                    )
                else:
                    return await self._default_load(
                        cache_key, func, self, *args, **kwargs
                    )

            return wrapper

        return decorator

    # Background warming

    async def start_background_warming(
        self,
        warming_config: List[Dict[str, Any]],
        interval: int = 3600,  # 1 hour
        concurrency: int = 5,
    ) -> None:
        """Start background cache warming."""
        try:
            task = asyncio.create_task(
                self._background_warming_loop(warming_config, interval, concurrency)
            )
            self._warming_tasks.append(task)
            logger.info(f"Started background cache warming (interval: {interval}s)")

        except Exception as e:
            logger.error(f"Failed to start background warming: {e}")

    async def stop_background_warming(self) -> None:
        """Stop background cache warming."""
        try:
            for task in self._warming_tasks:
                if not task.done():
                    task.cancel()

            if self._warming_tasks:
                await asyncio.gather(*self._warming_tasks, return_exceptions=True)
                self._warming_tasks.clear()

            logger.info("Stopped background cache warming")

        except Exception as e:
            logger.error(f"Failed to stop background warming: {e}")

    async def _background_warming_loop(
        self, warming_config: List[Dict[str, Any]], interval: int, concurrency: int
    ) -> None:
        """Background warming loop."""
        while True:
            try:
                await asyncio.sleep(interval)
                await self.warm_cache(warming_config, concurrency)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Background warming failed: {e}")

    # Cleanup and monitoring

    async def cleanup(self) -> None:
        """Cleanup cache loader resources."""
        try:
            # Stop background warming
            await self.stop_background_warming()

            # Clear loader registry
            self._loaders.clear()
            self._loader_metadata.clear()

            logger.debug("Cache loader cleanup completed")

        except Exception as e:
            logger.error(f"Cache loader cleanup failed: {e}")

    def get_health_status(self) -> Dict[str, Any]:
        """Get cache loader health status."""
        return {
            "is_healthy": True,
            "total_loaders": len(self._loaders),
            "warming_tasks": len(self._warming_tasks),
            "metrics_enabled": self.enable_metrics,
            "logging_enabled": self.enable_logging,
            "stats": self.get_loader_stats(),
        }
