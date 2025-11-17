"""
Cache reloader module for ncm-foundation.

This module provides cache reloading functionality including:
- Automatic cache reloading
- Cache warming
- Background refresh
- Cache invalidation
- Performance monitoring
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class ReloadStrategy(Enum):
    """Cache reload strategy enumeration."""

    LAZY = "lazy"  # Reload on access
    EAGER = "eager"  # Reload immediately
    BACKGROUND = "background"  # Reload in background
    SCHEDULED = "scheduled"  # Reload on schedule


class ReloadTrigger(Enum):
    """Cache reload trigger enumeration."""

    TIME_BASED = "time_based"  # Based on TTL
    ACCESS_BASED = "access_based"  # Based on access count
    EVENT_BASED = "event_based"  # Based on events
    MANUAL = "manual"  # Manual trigger


class CacheReloader:
    """Cache reloader implementation with advanced features."""

    def __init__(
        self,
        cache,
        default_ttl: int = 3600,
        reload_threshold: float = 0.8,  # Reload when 80% of TTL has passed
        max_concurrent_reloads: int = 10,
        enable_background_reload: bool = True,
        enable_metrics: bool = True,
    ):
        self.cache = cache
        self.default_ttl = default_ttl
        self.reload_threshold = reload_threshold
        self.max_concurrent_reloads = max_concurrent_reloads
        self.enable_background_reload = enable_background_reload
        self.enable_metrics = enable_metrics

        # Reload tracking
        self._reload_tasks: Dict[str, asyncio.Task] = {}
        self._reload_semaphore = asyncio.Semaphore(max_concurrent_reloads)
        self._reload_callbacks: Dict[str, List[Callable]] = {}
        self._reload_schedules: Dict[str, Dict[str, Any]] = {}

        # Metrics
        self._reload_count = 0
        self._reload_success_count = 0
        self._reload_error_count = 0
        self._reload_time = 0.0
        self._background_reload_count = 0

        # Background tasks
        self._background_tasks: List[asyncio.Task] = []
        self._scheduler_task: Optional[asyncio.Task] = None

        # Start background scheduler if enabled
        if self.enable_background_reload:
            self._start_background_scheduler()

    def _start_background_scheduler(self) -> None:
        """Start background scheduler for scheduled reloads."""
        if self._scheduler_task is None or self._scheduler_task.done():
            self._scheduler_task = asyncio.create_task(
                self._background_scheduler_loop()
            )

    async def _background_scheduler_loop(self) -> None:
        """Background scheduler loop for scheduled reloads."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                await self._process_scheduled_reloads()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Background scheduler failed: {e}")

    async def _process_scheduled_reloads(self) -> None:
        """Process scheduled reloads."""
        try:
            current_time = time.time()

            for key, schedule_info in self._reload_schedules.items():
                next_reload = schedule_info.get("next_reload", 0)

                if current_time >= next_reload:
                    # Trigger reload
                    await self.reload_key(key, strategy=ReloadStrategy.BACKGROUND)

                    # Update next reload time
                    interval = schedule_info.get("interval", self.default_ttl)
                    self._reload_schedules[key]["next_reload"] = current_time + interval

        except Exception as e:
            logger.error(f"Scheduled reload processing failed: {e}")

    async def reload_key(
        self,
        key: str,
        loader: Optional[Callable[[], Awaitable[Any]]] = None,
        strategy: ReloadStrategy = ReloadStrategy.LAZY,
        ttl: Optional[int] = None,
        force: bool = False,
    ) -> bool:
        """Reload cache key with specified strategy."""
        try:
            # Check if already reloading
            if key in self._reload_tasks and not self._reload_tasks[key].done():
                if not force:
                    logger.debug(f"Key {key} is already being reloaded")
                    return False

            # Check if reload is needed
            if not force and not await self._should_reload(key):
                return True

            # Create reload task
            if strategy == ReloadStrategy.BACKGROUND:
                task = asyncio.create_task(self._background_reload(key, loader, ttl))
                self._reload_tasks[key] = task
                return True
            else:
                # Immediate reload
                return await self._immediate_reload(key, loader, ttl)

        except Exception as e:
            logger.error(f"Reload key failed for {key}: {e}")
            return False

    async def _should_reload(self, key: str) -> bool:
        """Check if key should be reloaded."""
        try:
            # Check if key exists
            if not await self.cache.exists(key):
                return True

            # Get TTL
            ttl = await self.cache.get_ttl(key)
            if ttl is None:
                return True

            # Check if TTL is below threshold
            threshold_ttl = self.default_ttl * self.reload_threshold
            return ttl <= threshold_ttl

        except Exception as e:
            logger.error(f"Should reload check failed for key {key}: {e}")
            return True

    async def _immediate_reload(
        self,
        key: str,
        loader: Optional[Callable[[], Awaitable[Any]]] = None,
        ttl: Optional[int] = None,
    ) -> bool:
        """Perform immediate reload."""
        try:
            async with self._reload_semaphore:
                start_time = time.time()

                if loader is None:
                    # Try to get existing loader
                    loader = self._get_loader_for_key(key)
                    if loader is None:
                        logger.warning(f"No loader available for key {key}")
                        return False

                # Load new value
                new_value = await loader()

                # Store in cache
                await self.cache.set(key, new_value, ttl or self.default_ttl)

                # Update metrics
                reload_time = time.time() - start_time
                self._reload_count += 1
                self._reload_success_count += 1
                self._reload_time += reload_time

                # Execute callbacks
                await self._execute_reload_callbacks(key, new_value)

                logger.debug(
                    f"Immediate reload completed for key {key} in {reload_time:.3f}s"
                )
                return True

        except Exception as e:
            self._reload_error_count += 1
            logger.error(f"Immediate reload failed for key {key}: {e}")
            return False

    async def _background_reload(
        self,
        key: str,
        loader: Optional[Callable[[], Awaitable[Any]]] = None,
        ttl: Optional[int] = None,
    ) -> bool:
        """Perform background reload."""
        try:
            async with self._reload_semaphore:
                start_time = time.time()

                if loader is None:
                    # Try to get existing loader
                    loader = self._get_loader_for_key(key)
                    if loader is None:
                        logger.warning(f"No loader available for key {key}")
                        return False

                # Load new value
                new_value = await loader()

                # Store in cache
                await self.cache.set(key, new_value, ttl or self.default_ttl)

                # Update metrics
                reload_time = time.time() - start_time
                self._reload_count += 1
                self._reload_success_count += 1
                self._reload_time += reload_time
                self._background_reload_count += 1

                # Execute callbacks
                await self._execute_reload_callbacks(key, new_value)

                logger.debug(
                    f"Background reload completed for key {key} in {reload_time:.3f}s"
                )
                return True

        except Exception as e:
            self._reload_error_count += 1
            logger.error(f"Background reload failed for key {key}: {e}")
            return False
        finally:
            # Remove from active tasks
            if key in self._reload_tasks:
                del self._reload_tasks[key]

    def _get_loader_for_key(self, key: str) -> Optional[Callable]:
        """Get loader function for key."""
        # This would be implemented based on how loaders are registered
        # For now, return None
        return None

    async def _execute_reload_callbacks(self, key: str, value: Any) -> None:
        """Execute reload callbacks for key."""
        try:
            if key in self._reload_callbacks:
                for callback in self._reload_callbacks[key]:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(key, value)
                        else:
                            callback(key, value)
                    except Exception as e:
                        logger.error(f"Reload callback failed for key {key}: {e}")

        except Exception as e:
            logger.error(f"Execute reload callbacks failed for key {key}: {e}")

    def register_loader(
        self,
        key: str,
        loader: Callable[[], Awaitable[Any]],
        ttl: Optional[int] = None,
        strategy: ReloadStrategy = ReloadStrategy.LAZY,
        schedule_interval: Optional[int] = None,
    ) -> None:
        """Register loader for key."""
        try:
            # Store loader info
            self._reload_callbacks[key] = []

            # Set up scheduled reload if specified
            if schedule_interval is not None:
                self._reload_schedules[key] = {
                    "interval": schedule_interval,
                    "next_reload": time.time() + schedule_interval,
                    "strategy": strategy,
                }

            logger.debug(f"Registered loader for key: {key}")

        except Exception as e:
            logger.error(f"Failed to register loader for key {key}: {e}")

    def add_reload_callback(
        self, key: str, callback: Callable[[str, Any], Union[None, Awaitable[None]]]
    ) -> None:
        """Add reload callback for key."""
        try:
            if key not in self._reload_callbacks:
                self._reload_callbacks[key] = []

            self._reload_callbacks[key].append(callback)
            logger.debug(f"Added reload callback for key: {key}")

        except Exception as e:
            logger.error(f"Failed to add reload callback for key {key}: {e}")

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
                        key = item_config["key"]
                        loader = item_config["loader"]
                        ttl = item_config.get("ttl", self.default_ttl)

                        # Register loader
                        self.register_loader(key, loader, ttl)

                        # Perform initial load
                        await self.reload_key(key, loader, ReloadStrategy.EAGER, ttl)
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

    async def invalidate_and_reload(
        self,
        key: str,
        loader: Optional[Callable[[], Awaitable[Any]]] = None,
        ttl: Optional[int] = None,
    ) -> bool:
        """Invalidate key and reload immediately."""
        try:
            # Delete from cache
            await self.cache.delete(key)

            # Reload if loader provided
            if loader is not None:
                return await self.reload_key(
                    key, loader, ReloadStrategy.EAGER, ttl, force=True
                )

            return True

        except Exception as e:
            logger.error(f"Invalidate and reload failed for key {key}: {e}")
            return False

    async def schedule_reload(
        self,
        key: str,
        interval: int,
        loader: Optional[Callable[[], Awaitable[Any]]] = None,
        ttl: Optional[int] = None,
    ) -> bool:
        """Schedule periodic reload for key."""
        try:
            # Register loader if provided
            if loader is not None:
                self.register_loader(
                    key, loader, ttl, ReloadStrategy.SCHEDULED, interval
                )
            else:
                # Update existing schedule
                if key in self._reload_schedules:
                    self._reload_schedules[key]["interval"] = interval
                    self._reload_schedules[key]["next_reload"] = time.time() + interval
                else:
                    logger.warning(
                        f"No loader registered for scheduled reload of key {key}"
                    )
                    return False

            logger.debug(f"Scheduled reload for key {key} every {interval}s")
            return True

        except Exception as e:
            logger.error(f"Schedule reload failed for key {key}: {e}")
            return False

    async def cancel_scheduled_reload(self, key: str) -> bool:
        """Cancel scheduled reload for key."""
        try:
            if key in self._reload_schedules:
                del self._reload_schedules[key]
                logger.debug(f"Cancelled scheduled reload for key {key}")
                return True

            return False

        except Exception as e:
            logger.error(f"Cancel scheduled reload failed for key {key}: {e}")
            return False

    def get_reload_stats(self) -> Dict[str, Any]:
        """Get reload statistics."""
        avg_reload_time = (
            self._reload_time / self._reload_count if self._reload_count > 0 else 0
        )
        success_rate = (
            self._reload_success_count / self._reload_count
            if self._reload_count > 0
            else 0
        )

        return {
            "total_reloads": self._reload_count,
            "successful_reloads": self._reload_success_count,
            "failed_reloads": self._reload_error_count,
            "success_rate": success_rate,
            "avg_reload_time": avg_reload_time,
            "background_reloads": self._background_reload_count,
            "active_reloads": len(self._reload_tasks),
            "scheduled_reloads": len(self._reload_schedules),
            "registered_callbacks": sum(
                len(callbacks) for callbacks in self._reload_callbacks.values()
            ),
        }

    async def cleanup(self) -> None:
        """Cleanup reloader resources."""
        try:
            # Cancel all active reload tasks
            for task in self._reload_tasks.values():
                if not task.done():
                    task.cancel()

            if self._reload_tasks:
                await asyncio.gather(
                    *self._reload_tasks.values(), return_exceptions=True
                )
                self._reload_tasks.clear()

            # Cancel background scheduler
            if self._scheduler_task and not self._scheduler_task.done():
                self._scheduler_task.cancel()
                try:
                    await self._scheduler_task
                except asyncio.CancelledError:
                    pass

            # Clear all data
            self._reload_callbacks.clear()
            self._reload_schedules.clear()

            logger.debug("Cache reloader cleanup completed")

        except Exception as e:
            logger.error(f"Cache reloader cleanup failed: {e}")

    # Decorator for automatic reloading
    def auto_reload(
        self,
        ttl: Optional[int] = None,
        strategy: ReloadStrategy = ReloadStrategy.LAZY,
        schedule_interval: Optional[int] = None,
    ):
        """Decorator for automatic cache reloading."""

        def decorator(func: Callable) -> Callable:
            async def wrapper(*args, **kwargs):
                # Generate cache key
                cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"

                # Register loader
                self.register_loader(
                    cache_key,
                    lambda: func(*args, **kwargs),
                    ttl,
                    strategy,
                    schedule_interval,
                )

                # Try to get from cache first
                value = await self.cache.get(cache_key)
                if value is not None:
                    # Check if reload is needed
                    if await self._should_reload(cache_key):
                        await self.reload_key(cache_key, strategy=strategy)
                        value = await self.cache.get(cache_key)
                    return value

                # Cache miss - load and cache
                value = await func(*args, **kwargs)
                await self.cache.set(cache_key, value, ttl or self.default_ttl)
                return value

            return wrapper

        return decorator
