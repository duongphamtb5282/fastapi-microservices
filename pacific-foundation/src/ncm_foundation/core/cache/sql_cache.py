"""
SQL query caching implementation for ncm-foundation.

This module provides specialized SQL query caching functionality including:
- Query result caching
- Query invalidation
- Cache warming
- Query performance monitoring
"""

import asyncio
import hashlib
import json
import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union

from .redis_cache import CacheStrategy, RedisCache, SerializationType

logger = logging.getLogger(__name__)


class QueryCacheStrategy(Enum):
    """SQL query cache strategies."""

    CACHE_FIRST = "cache_first"  # Try cache first, fallback to DB
    DB_FIRST = "db_first"  # Try DB first, cache result
    CACHE_ONLY = "cache_only"  # Only use cache, no DB fallback
    DB_ONLY = "db_only"  # Only use DB, no caching


class SQLCache:
    """SQL query cache implementation."""

    def __init__(
        self,
        redis_cache: RedisCache,
        default_ttl: int = 3600,
        max_query_size: int = 1024 * 1024,  # 1MB
        enable_query_logging: bool = True,
        enable_performance_monitoring: bool = True,
    ):
        self.redis_cache = redis_cache
        self.default_ttl = default_ttl
        self.max_query_size = max_query_size
        self.enable_query_logging = enable_query_logging
        self.enable_performance_monitoring = enable_performance_monitoring

        # Performance metrics
        self._query_hits = 0
        self._query_misses = 0
        self._query_errors = 0
        self._total_query_time = 0.0
        self._cache_hit_time = 0.0
        self._db_hit_time = 0.0

        # Query patterns for invalidation
        self._query_patterns: Dict[str, List[str]] = {}

        # Cache warming
        self._warming_queries: List[Dict[str, Any]] = []

    def _generate_query_key(
        self, sql: str, params: Optional[Dict] = None, db_name: Optional[str] = None
    ) -> str:
        """Generate cache key for SQL query."""
        # Create hash of SQL and parameters
        content = sql.strip().lower()
        if params:
            # Sort parameters for consistent hashing
            sorted_params = json.dumps(params, sort_keys=True)
            content += sorted_params
        if db_name:
            content += f":{db_name}"

        hash_obj = hashlib.sha256(content.encode("utf-8"))
        return f"sql:{hash_obj.hexdigest()}"

    def _log_query(
        self,
        sql: str,
        params: Optional[Dict] = None,
        hit: bool = False,
        execution_time: float = 0.0,
        error: Optional[str] = None,
    ) -> None:
        """Log query execution."""
        if not self.enable_query_logging:
            return

        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "sql": sql[:100] + "..." if len(sql) > 100 else sql,
            "params": params,
            "hit": hit,
            "execution_time": execution_time,
            "error": error,
        }

        if hit:
            logger.debug(f"SQL cache hit: {log_data}")
        else:
            logger.debug(f"SQL cache miss: {log_data}")

    async def cache_query(
        self,
        sql: str,
        params: Optional[Dict] = None,
        ttl: Optional[int] = None,
        strategy: QueryCacheStrategy = QueryCacheStrategy.CACHE_FIRST,
        db_name: Optional[str] = None,
        key_suffix: Optional[str] = None,
    ) -> Optional[Any]:
        """Cache SQL query with specified strategy."""
        start_time = time.time()
        cache_key = self._generate_query_key(sql, params, db_name)

        if key_suffix:
            cache_key += f":{key_suffix}"

        try:
            if strategy == QueryCacheStrategy.CACHE_FIRST:
                return await self._cache_first_strategy(
                    cache_key, sql, params, ttl, start_time
                )
            elif strategy == QueryCacheStrategy.DB_FIRST:
                return await self._db_first_strategy(
                    cache_key, sql, params, ttl, start_time
                )
            elif strategy == QueryCacheStrategy.CACHE_ONLY:
                return await self._cache_only_strategy(cache_key, start_time)
            elif strategy == QueryCacheStrategy.DB_ONLY:
                return await self._db_only_strategy(sql, params, start_time)
            else:
                raise ValueError(f"Unknown query cache strategy: {strategy}")

        except Exception as e:
            self._query_errors += 1
            execution_time = time.time() - start_time
            self._log_query(sql, params, False, execution_time, str(e))
            logger.error(f"SQL query cache failed: {e}")
            return None

    async def _cache_first_strategy(
        self,
        cache_key: str,
        sql: str,
        params: Optional[Dict] = None,
        ttl: Optional[int] = None,
        start_time: float = 0.0,
    ) -> Optional[Any]:
        """Cache-first strategy implementation."""
        # Try cache first
        cache_start = time.time()
        result = await self.redis_cache.get(cache_key)
        cache_time = time.time() - cache_start

        if result is not None:
            # Cache hit
            self._query_hits += 1
            self._cache_hit_time += cache_time
            execution_time = time.time() - start_time
            self._log_query(sql, params, True, execution_time)
            return result

        # Cache miss - would need DB execution here
        # This is a placeholder - in real implementation, you'd execute the query
        logger.debug(f"Cache miss for query: {sql[:50]}...")
        self._query_misses += 1

        # Simulate DB execution
        await asyncio.sleep(0.01)  # Simulate DB query time
        result = {
            "data": "simulated_db_result",
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Cache the result
        await self.redis_cache.set(cache_key, result, ttl or self.default_ttl)

        db_time = time.time() - start_time - cache_time
        self._db_hit_time += db_time
        execution_time = time.time() - start_time
        self._log_query(sql, params, False, execution_time)

        return result

    async def _db_first_strategy(
        self,
        cache_key: str,
        sql: str,
        params: Optional[Dict] = None,
        ttl: Optional[int] = None,
        start_time: float = 0.0,
    ) -> Optional[Any]:
        """DB-first strategy implementation."""
        # Execute DB query first
        db_start = time.time()
        # Simulate DB execution
        await asyncio.sleep(0.01)
        result = {
            "data": "simulated_db_result",
            "timestamp": datetime.utcnow().isoformat(),
        }
        db_time = time.time() - db_start

        # Cache the result
        await self.redis_cache.set(cache_key, result, ttl or self.default_ttl)

        self._query_misses += 1
        self._db_hit_time += db_time
        execution_time = time.time() - start_time
        self._log_query(sql, params, False, execution_time)

        return result

    async def _cache_only_strategy(
        self, cache_key: str, start_time: float = 0.0
    ) -> Optional[Any]:
        """Cache-only strategy implementation."""
        cache_start = time.time()
        result = await self.redis_cache.get(cache_key)
        cache_time = time.time() - cache_start

        if result is not None:
            self._query_hits += 1
            self._cache_hit_time += cache_time
        else:
            self._query_misses += 1

        execution_time = time.time() - start_time
        self._log_query("cache_only_query", None, result is not None, execution_time)

        return result

    async def _db_only_strategy(
        self, sql: str, params: Optional[Dict] = None, start_time: float = 0.0
    ) -> Optional[Any]:
        """DB-only strategy implementation."""
        # Execute DB query without caching
        db_start = time.time()
        # Simulate DB execution
        await asyncio.sleep(0.01)
        result = {
            "data": "simulated_db_result",
            "timestamp": datetime.utcnow().isoformat(),
        }
        db_time = time.time() - db_start

        self._query_misses += 1
        self._db_hit_time += db_time
        execution_time = time.time() - start_time
        self._log_query(sql, params, False, execution_time)

        return result

    async def invalidate_query(
        self, sql: str, params: Optional[Dict] = None, db_name: Optional[str] = None
    ) -> bool:
        """Invalidate specific query cache."""
        try:
            cache_key = self._generate_query_key(sql, params, db_name)
            success = await self.redis_cache.delete(cache_key)

            if success:
                logger.debug(f"Invalidated query cache: {sql[:50]}...")

            return success

        except Exception as e:
            logger.error(f"Query invalidation failed: {e}")
            return False

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate queries matching pattern."""
        try:
            sql_pattern = f"sql:{pattern}"
            count = await self.redis_cache.clear_pattern(sql_pattern)

            logger.debug(f"Invalidated {count} queries matching pattern: {pattern}")
            return count

        except Exception as e:
            logger.error(f"Pattern invalidation failed: {e}")
            return 0

    async def invalidate_table(self, table_name: str) -> int:
        """Invalidate all queries related to a table."""
        try:
            # Common patterns for table-related queries
            patterns = [
                f"*{table_name}*",
                f"*FROM {table_name}*",
                f"*INTO {table_name}*",
                f"*UPDATE {table_name}*",
                f"*DELETE FROM {table_name}*",
            ]

            total_count = 0
            for pattern in patterns:
                count = await self.invalidate_pattern(pattern)
                total_count += count

            logger.debug(f"Invalidated {total_count} queries for table: {table_name}")
            return total_count

        except Exception as e:
            logger.error(f"Table invalidation failed: {e}")
            return 0

    async def warm_cache(
        self, queries: List[Dict[str, Any]], concurrency: int = 5
    ) -> Dict[str, Any]:
        """Warm cache with predefined queries."""
        try:
            results = {
                "total_queries": len(queries),
                "successful": 0,
                "failed": 0,
                "errors": [],
            }

            # Process queries in batches
            semaphore = asyncio.Semaphore(concurrency)

            async def process_query(query_data: Dict[str, Any]) -> None:
                async with semaphore:
                    try:
                        sql = query_data["sql"]
                        params = query_data.get("params")
                        ttl = query_data.get("ttl", self.default_ttl)
                        strategy = QueryCacheStrategy(
                            query_data.get("strategy", "cache_first")
                        )

                        await self.cache_query(sql, params, ttl, strategy)
                        results["successful"] += 1

                    except Exception as e:
                        results["failed"] += 1
                        results["errors"].append(str(e))
                        logger.error(f"Cache warming failed for query: {e}")

            # Execute all queries
            tasks = [process_query(query) for query in queries]
            await asyncio.gather(*tasks, return_exceptions=True)

            logger.info(
                f"Cache warming completed: {results['successful']}/{results['total_queries']} successful"
            )
            return results

        except Exception as e:
            logger.error(f"Cache warming failed: {e}")
            return {"error": str(e)}

    def register_query_pattern(
        self, pattern_name: str, sql_patterns: List[str]
    ) -> None:
        """Register query patterns for invalidation."""
        self._query_patterns[pattern_name] = sql_patterns
        logger.debug(
            f"Registered query pattern: {pattern_name} with {len(sql_patterns)} patterns"
        )

    async def invalidate_by_pattern_name(self, pattern_name: str) -> int:
        """Invalidate queries by registered pattern name."""
        if pattern_name not in self._query_patterns:
            logger.warning(f"Unknown pattern name: {pattern_name}")
            return 0

        total_count = 0
        for pattern in self._query_patterns[pattern_name]:
            count = await self.invalidate_pattern(pattern)
            total_count += count

        logger.debug(f"Invalidated {total_count} queries for pattern: {pattern_name}")
        return total_count

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get SQL cache performance statistics."""
        total_queries = self._query_hits + self._query_misses
        hit_rate = self._query_hits / total_queries if total_queries > 0 else 0

        avg_cache_time = (
            self._cache_hit_time / self._query_hits if self._query_hits > 0 else 0
        )
        avg_db_time = (
            self._db_hit_time / self._query_misses if self._query_misses > 0 else 0
        )

        return {
            "query_hits": self._query_hits,
            "query_misses": self._query_misses,
            "query_errors": self._query_errors,
            "hit_rate": hit_rate,
            "total_queries": total_queries,
            "avg_cache_time": avg_cache_time,
            "avg_db_time": avg_db_time,
            "total_cache_time": self._cache_hit_time,
            "total_db_time": self._db_hit_time,
            "registered_patterns": len(self._query_patterns),
        }

    async def clear_all_queries(self) -> bool:
        """Clear all SQL query cache."""
        try:
            success = await self.redis_cache.clear_pattern("sql:*")
            logger.info(f"Cleared all SQL query cache: {success} keys")
            return success

        except Exception as e:
            logger.error(f"Clear all queries failed: {e}")
            return False

    async def get_query_info(
        self, sql: str, params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Get information about a cached query."""
        try:
            cache_key = self._generate_query_key(sql, params)
            exists = await self.redis_cache.exists(cache_key)
            ttl = await self.redis_cache.get_ttl(cache_key) if exists else None

            return {
                "sql": sql,
                "params": params,
                "cache_key": cache_key,
                "exists": exists,
                "ttl": ttl,
                "size": len(sql) + (len(str(params)) if params else 0),
            }

        except Exception as e:
            logger.error(f"Get query info failed: {e}")
            return {"error": str(e)}

    # Cache Loader for SQL Queries
    def sql_cache_loader(
        self,
        ttl: Optional[int] = None,
        strategy: QueryCacheStrategy = QueryCacheStrategy.CACHE_FIRST,
        key_suffix: Optional[str] = None,
    ):
        """SQL cache loader decorator."""

        def decorator(func: Callable) -> Callable:
            async def wrapper(*args, **kwargs):
                # Extract SQL and params from function arguments
                sql = args[0] if args else ""
                params = args[1] if len(args) > 1 else None

                # Generate cache key
                cache_key = self._generate_query_key(sql, params)
                if key_suffix:
                    cache_key += f":{key_suffix}"

                # Use specified strategy
                if strategy == QueryCacheStrategy.CACHE_FIRST:
                    # Try cache first
                    result = await self.redis_cache.get(cache_key)
                    if result is not None:
                        return result

                    # Execute function and cache result
                    result = await func(*args, **kwargs)
                    await self.redis_cache.set(
                        cache_key, result, ttl or self.default_ttl
                    )
                    return result

                elif strategy == QueryCacheStrategy.DB_FIRST:
                    # Execute function first, then cache
                    result = await func(*args, **kwargs)
                    await self.redis_cache.set(
                        cache_key, result, ttl or self.default_ttl
                    )
                    return result

                else:
                    # Default behavior
                    return await func(*args, **kwargs)

            return wrapper

        return decorator
