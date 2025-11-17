"""
Cache examples for ncm-foundation.

This module provides comprehensive examples of using the cache system
for different scenarios and use cases.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List

from .cache_loader import CacheLoader
from .cache_strategies import CacheStrategies, InvalidationStrategy
from .multi_level import CacheLevel, MultiLevelCache
from .redis_sync_cache import CacheStrategy, RedisSyncCache, SerializationType
from .reloader import CacheReloader, ReloadStrategy
from .serializers import CompressionType
from .serializers import SerializationType as SerializerType
from .serializers import SerializerFactory
from .sql_cache import QueryCacheStrategy, SQLCache

logger = logging.getLogger(__name__)


async def basic_redis_cache_example():
    """Example: Basic Redis cache usage."""
    print("=== Basic Redis Cache Example ===")

    # Create Redis cache
    cache = RedisSyncCache(
        host="localhost",
        port=6379,
        db=0,
        default_ttl=3600,
        strategy=CacheStrategy.CACHE_ASIDE,
        serialization=SerializationType.JSON,
        compression=True,
    )

    try:
        # Basic operations
        await cache.set("user:123", {"name": "John", "email": "john@example.com"})
        user = await cache.get("user:123")
        print(f"✅ Retrieved user: {user}")

        # Check if key exists
        exists = await cache.exists("user:123")
        print(f"✅ Key exists: {exists}")

        # Get TTL
        ttl = await cache.get_ttl("user:123")
        print(f"✅ TTL: {ttl}s")

        # Delete key
        await cache.delete("user:123")
        print("✅ Key deleted")

    except Exception as e:
        print(f"❌ Basic cache example failed: {e}")
    finally:
        await cache.close()


async def multi_level_cache_example():
    """Example: Multi-level cache usage."""
    print("\n=== Multi-Level Cache Example ===")

    # Create L2 cache (Redis)
    l2_cache = RedisSyncCache(host="localhost", port=6379, db=0, default_ttl=3600)

    # Create multi-level cache
    multi_cache = MultiLevelCache(
        l2_cache=l2_cache,
        l1_max_size=1000,
        l1_default_ttl=300,  # 5 minutes
        l2_default_ttl=3600,  # 1 hour
        enable_promotion=True,
        enable_stampede_prevention=True,
    )

    try:
        # Set value in multi-level cache
        await multi_cache.set(
            "product:456",
            {"id": 456, "name": "Laptop", "price": 999.99, "category": "Electronics"},
        )

        # Get value (will try L1 first, then L2)
        product = await multi_cache.get("product:456")
        print(f"✅ Retrieved product: {product}")

        # Get statistics
        stats = multi_cache.get_stats()
        print(f"✅ Cache stats: {stats['overall_stats']}")

    except Exception as e:
        print(f"❌ Multi-level cache example failed: {e}")
    finally:
        await multi_cache.close()


async def sql_cache_example():
    """Example: SQL query caching."""
    print("\n=== SQL Cache Example ===")

    # Create Redis cache
    cache = RedisSyncCache(host="localhost", port=6379, db=0)

    # Create SQL cache
    sql_cache = SQLCache(cache)

    try:
        # Cache SQL query
        result = await sql_cache.cache_query(
            "SELECT * FROM users WHERE active = %s",
            params={"active": True},
            strategy=QueryCacheStrategy.CACHE_FIRST,
            ttl=1800,
        )
        print(f"✅ SQL query result: {result}")

        # Get performance stats
        stats = sql_cache.get_performance_stats()
        print(f"✅ SQL cache stats: {stats}")

    except Exception as e:
        print(f"❌ SQL cache example failed: {e}")
    finally:
        await cache.close()


async def cache_strategies_example():
    """Example: Cache strategies usage."""
    print("\n=== Cache Strategies Example ===")

    # Create Redis cache
    cache = RedisSyncCache(host="localhost", port=6379, db=0)

    # Create cache strategies
    strategies = CacheStrategies(cache)

    try:
        # Write-through strategy
        await strategies.write_through(
            "user:789", {"name": "Alice", "email": "alice@example.com"}, ttl=3600
        )
        print("✅ Write-through strategy applied")

        # Write-behind strategy
        await strategies.write_behind(
            "user:101", {"name": "Bob", "email": "bob@example.com"}, ttl=3600
        )
        print("✅ Write-behind strategy applied")

        # Event-based invalidation
        await strategies.event_based_invalidation(
            "user_updated", keys=["user:789", "user:101"]
        )
        print("✅ Event-based invalidation registered")

        # Get strategy stats
        stats = strategies.get_strategy_stats()
        print(f"✅ Strategy stats: {stats}")

    except Exception as e:
        print(f"❌ Cache strategies example failed: {e}")
    finally:
        await strategies.close()


async def cache_loader_example():
    """Example: Cache loader usage."""
    print("\n=== Cache Loader Example ===")

    # Create Redis cache
    cache = RedisSyncCache(host="localhost", port=6379, db=0)

    # Create cache loader
    loader = CacheLoader(cache)

    # Define loader function
    async def load_user_data(user_id: int):
        # Simulate database query
        await asyncio.sleep(0.1)
        return {
            "id": user_id,
            "name": f"User {user_id}",
            "email": f"user{user_id}@example.com",
            "created_at": datetime.utcnow().isoformat(),
        }

    try:
        # Register loader
        loader.register_loader(
            "user_data", load_user_data, ttl=3600, strategy=CacheStrategy.CACHE_ASIDE
        )

        # Use loader
        user_data = await loader.load("user_data", user_id=123)
        print(f"✅ Loaded user data: {user_data}")

        # Get loader stats
        stats = loader.get_loader_stats()
        print(f"✅ Loader stats: {stats}")

    except Exception as e:
        print(f"❌ Cache loader example failed: {e}")
    finally:
        await loader.cleanup()


async def serialization_example():
    """Example: Cache serialization usage."""
    print("\n=== Serialization Example ===")

    # Create different serializers
    json_serializer = SerializerFactory.create_serializer(
        SerializerType.JSON, compression_type=CompressionType.GZIP
    )

    pickle_serializer = SerializerFactory.create_serializer(
        SerializerType.PICKLE, compression_type=CompressionType.NONE
    )

    try:
        # Test data
        test_data = {
            "id": 123,
            "name": "Test User",
            "data": [1, 2, 3, 4, 5],
            "nested": {"key": "value", "number": 42},
        }

        # JSON serialization
        json_data = json_serializer.serialize(test_data)
        json_deserialized = json_serializer.deserialize(json_data)
        print(f"✅ JSON serialization: {len(json_data)} bytes")

        # Pickle serialization
        pickle_data = pickle_serializer.serialize(test_data)
        pickle_deserialized = pickle_serializer.deserialize(pickle_data)
        print(f"✅ Pickle serialization: {len(pickle_data)} bytes")

        # Verify data integrity
        assert json_deserialized == test_data
        assert pickle_deserialized == test_data
        print("✅ Data integrity verified")

    except Exception as e:
        print(f"❌ Serialization example failed: {e}")


async def cache_reloader_example():
    """Example: Cache reloader usage."""
    print("\n=== Cache Reloader Example ===")

    # Create Redis cache
    cache = RedisSyncCache(host="localhost", port=6379, db=0)

    # Create cache reloader
    reloader = CacheReloader(cache)

    # Define loader function
    async def load_fresh_data():
        # Simulate data loading
        await asyncio.sleep(0.1)
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "data": "Fresh data from source",
        }

    try:
        # Register loader
        reloader.register_loader(
            "fresh_data",
            load_fresh_data,
            ttl=300,  # 5 minutes
            strategy=ReloadStrategy.LAZY,
        )

        # Add reload callback
        def reload_callback(key: str, value: Any):
            print(f"🔄 Reloaded {key}: {value}")

        reloader.add_reload_callback("fresh_data", reload_callback)

        # Schedule periodic reload
        await reloader.schedule_reload(
            "fresh_data", interval=60, loader=load_fresh_data  # Reload every minute
        )

        # Get reload stats
        stats = reloader.get_reload_stats()
        print(f"✅ Reloader stats: {stats}")

    except Exception as e:
        print(f"❌ Cache reloader example failed: {e}")
    finally:
        await reloader.cleanup()


async def cache_warming_example():
    """Example: Cache warming."""
    print("\n=== Cache Warming Example ===")

    # Create Redis cache
    cache = RedisSyncCache(host="localhost", port=6379, db=0)

    # Create cache loader
    loader = CacheLoader(cache)

    # Define warming configuration
    warming_config = [
        {"name": "user_data", "args": [1], "kwargs": {}},
        {"name": "user_data", "args": [2], "kwargs": {}},
        {"name": "user_data", "args": [3], "kwargs": {}},
    ]

    # Define loader function
    async def load_user_data(user_id: int):
        await asyncio.sleep(0.1)
        return {
            "id": user_id,
            "name": f"User {user_id}",
            "email": f"user{user_id}@example.com",
        }

    try:
        # Register loader
        loader.register_loader("user_data", load_user_data, ttl=3600)

        # Warm cache
        results = await loader.warm_cache(warming_config, concurrency=3)
        print(f"✅ Cache warming results: {results}")

    except Exception as e:
        print(f"❌ Cache warming example failed: {e}")
    finally:
        await loader.cleanup()


async def performance_monitoring_example():
    """Example: Performance monitoring."""
    print("\n=== Performance Monitoring Example ===")

    # Create Redis cache
    cache = RedisSyncCache(host="localhost", port=6379, db=0)

    try:
        # Perform operations
        for i in range(10):
            await cache.set(f"key_{i}", f"value_{i}", ttl=3600)
            await cache.get(f"key_{i}")

        # Get performance stats
        stats = cache.get_stats()
        print(f"✅ Cache performance stats:")
        print(f"   Hits: {stats['hits']}")
        print(f"   Misses: {stats['misses']}")
        print(f"   Hit Rate: {stats['hit_rate']:.2%}")
        print(f"   Total Requests: {stats['total_requests']}")
        print(f"   Errors: {stats['errors']}")

        # Health check
        is_healthy = await cache.health_check()
        print(f"✅ Cache healthy: {is_healthy}")

    except Exception as e:
        print(f"❌ Performance monitoring example failed: {e}")
    finally:
        await cache.close()


async def complete_integration_example():
    """Example: Complete cache system integration."""
    print("\n=== Complete Integration Example ===")

    # Create Redis cache
    cache = RedisSyncCache(
        host="localhost",
        port=6379,
        db=0,
        default_ttl=3600,
        strategy=CacheStrategy.CACHE_ASIDE,
        serialization=SerializationType.JSON,
        compression=True,
    )

    # Create multi-level cache
    multi_cache = MultiLevelCache(
        l2_cache=cache, l1_max_size=100, enable_promotion=True
    )

    # Create SQL cache
    sql_cache = SQLCache(cache)

    # Create cache strategies
    strategies = CacheStrategies(cache)

    # Create cache loader
    loader = CacheLoader(cache)

    # Create cache reloader
    reloader = CacheReloader(cache)

    try:
        # Define loader function
        async def load_product_data(product_id: int):
            await asyncio.sleep(0.1)
            return {
                "id": product_id,
                "name": f"Product {product_id}",
                "price": 99.99,
                "category": "Electronics",
            }

        # Register loader
        loader.register_loader("product_data", load_product_data, ttl=1800)

        # Use multi-level cache
        product = await multi_cache.get(
            "product:123", loader=lambda: load_product_data(123)
        )
        print(f"✅ Multi-level cache result: {product}")

        # Use SQL cache
        sql_result = await sql_cache.cache_query(
            "SELECT * FROM products WHERE id = %s",
            params={"id": 123},
            strategy=QueryCacheStrategy.CACHE_FIRST,
        )
        print(f"✅ SQL cache result: {sql_result}")

        # Use cache strategies
        await strategies.write_through(
            "user:456", {"name": "John", "email": "john@example.com"}, ttl=3600
        )
        print("✅ Write-through strategy applied")

        # Get comprehensive stats
        cache_stats = cache.get_stats()
        multi_stats = multi_cache.get_stats()
        sql_stats = sql_cache.get_performance_stats()
        strategy_stats = strategies.get_strategy_stats()
        loader_stats = loader.get_loader_stats()
        reloader_stats = reloader.get_reload_stats()

        print(f"✅ Comprehensive stats:")
        print(f"   Cache Hit Rate: {cache_stats['hit_rate']:.2%}")
        print(
            f"   Multi-level Hit Rate: {multi_stats['overall_stats']['overall_hit_rate']:.2%}"
        )
        print(f"   SQL Hit Rate: {sql_stats['hit_rate']:.2%}")
        print(f"   Strategy Operations: {strategy_stats['write_through_count']}")
        print(f"   Loader Operations: {loader_stats['total_loads']}")
        print(f"   Reloader Operations: {reloader_stats['total_reloads']}")

    except Exception as e:
        print(f"❌ Complete integration example failed: {e}")
    finally:
        # Cleanup all components
        await multi_cache.close()
        await strategies.close()
        await loader.cleanup()
        await reloader.cleanup()
        await cache.close()


async def main():
    """Run all cache examples."""
    print("NCM-Foundation Cache Examples")
    print("=" * 50)

    # Run examples
    await basic_redis_cache_example()
    await multi_level_cache_example()
    await sql_cache_example()
    await cache_strategies_example()
    await cache_loader_example()
    await serialization_example()
    await cache_reloader_example()
    await cache_warming_example()
    await performance_monitoring_example()
    await complete_integration_example()

    print("\n" + "=" * 50)
    print("All cache examples completed!")
    print("\nFor more information, see:")
    print("- README.md for detailed documentation")
    print("- examples.py for code examples")
    print("- Individual module documentation")


if __name__ == "__main__":
    asyncio.run(main())
