# Redis-Based Caching System for NCM-Foundation

A comprehensive Redis-based caching system for ncm-foundation that provides advanced caching capabilities including multi-level caching, SQL query caching, multiple cache strategies, intelligent cache loaders, serialization support, and automatic cache reloading.

## Features

- **Redis Integration**: Full Redis support with connection pooling using synchronous redis library
- **Multi-Level Caching**: L1 (Memory) and L2 (Redis) cache levels with automatic promotion
- **SQL Query Caching**: Specialized caching for database queries with multiple strategies
- **Cache Strategies**: Write-through, write-behind, cache-aside, read-through
- **Cache Loaders**: Automatic cache loading with decorators and background warming
- **Cache Reloading**: Automatic cache refresh with multiple reload strategies
- **Serialization Support**: JSON, Pickle, MessagePack, and ORJSON serialization
- **Compression**: Optional data compression for large values (GZIP, LZ4, ZSTD)
- **Performance Monitoring**: Comprehensive metrics and statistics
- **TTL Management**: Flexible time-to-live configuration
- **Cache Invalidation**: Multiple invalidation strategies
- **Stampede Prevention**: Cache stampede protection for high-concurrency scenarios

## Quick Start

### 1. Installation

```bash
pip install redis
pip install ncm-foundation
```

### 2. Basic Usage

```python
from ncm_foundation.core.cache import RedisSyncCache, CacheStrategy

# Create Redis cache
cache = RedisSyncCache(
    host="localhost",
    port=6379,
    db=0,
    default_ttl=3600,
    strategy=CacheStrategy.CACHE_ASIDE
)

# Basic operations
await cache.set("user:123", {"name": "John", "email": "john@example.com"})
user = await cache.get("user:123")
await cache.delete("user:123")
```

### 3. Multi-Level Cache Usage

```python
from ncm_foundation.core.cache import RedisSyncCache, MultiLevelCache

# Create L2 cache (Redis)
l2_cache = RedisSyncCache(host="localhost", port=6379, db=0)

# Create multi-level cache
multi_cache = MultiLevelCache(
    l2_cache=l2_cache,
    l1_max_size=1000,
    l1_default_ttl=300,  # 5 minutes
    l2_default_ttl=3600,  # 1 hour
    enable_promotion=True,
    enable_stampede_prevention=True
)

# Use multi-level cache
await multi_cache.set("product:456", {"name": "Laptop", "price": 999.99})
product = await multi_cache.get("product:456")
```

### 3. SQL Query Caching

```python
from ncm_foundation.core.cache import SQLCache, QueryCacheStrategy

# Create SQL cache
sql_cache = SQLCache(cache)

# Cache SQL query
result = await sql_cache.cache_query(
    "SELECT * FROM users WHERE id = %s",
    params={"id": 123},
    strategy=QueryCacheStrategy.CACHE_FIRST,
    ttl=1800
)
```

## Architecture

### Core Components

1. **RedisSyncCache**: Main Redis cache implementation using synchronous redis library
2. **MultiLevelCache**: L1 (Memory) and L2 (Redis) multi-level caching
3. **SQLCache**: Specialized SQL query caching
4. **CacheStrategies**: Advanced cache strategies
5. **CacheLoader**: Intelligent cache loading
6. **CacheReloader**: Automatic cache reloading
7. **Serializers**: Multiple serialization formats with compression

### Cache Strategies

#### 1. Write-Through

```python
# Write to cache and persistent storage simultaneously
await cache.write_through("key", value, ttl=3600)
```

#### 2. Write-Behind

```python
# Write to cache immediately, persist in background
await cache.write_behind("key", value, ttl=3600)
```

#### 3. Cache-Aside

```python
# Application manages cache explicitly
value = await cache.get("key")
if value is None:
    value = await load_from_source()
    await cache.set("key", value, ttl=3600)
```

#### 4. Read-Through

```python
# Cache automatically loads from source on miss
value = await cache.read_through("key", loader_function, ttl=3600)
```

## SQL Query Caching

### Basic SQL Caching

```python
from ncm_foundation.core.cache import SQLCache, QueryCacheStrategy

sql_cache = SQLCache(redis_cache)

# Cache query with different strategies
result = await sql_cache.cache_query(
    "SELECT * FROM users WHERE active = %s",
    params={"active": True},
    strategy=QueryCacheStrategy.CACHE_FIRST,
    ttl=1800
)
```

### SQL Cache Strategies

#### 1. Cache-First Strategy

```python
# Try cache first, fallback to database
result = await sql_cache.cache_query(
    "SELECT * FROM products WHERE category = %s",
    params={"category": "electronics"},
    strategy=QueryCacheStrategy.CACHE_FIRST
)
```

#### 2. DB-First Strategy

```python
# Query database first, cache result
result = await sql_cache.cache_query(
    "SELECT COUNT(*) FROM orders WHERE date >= %s",
    params={"date": "2024-01-01"},
    strategy=QueryCacheStrategy.DB_FIRST
)
```

#### 3. Cache-Only Strategy

```python
# Only use cache, no database fallback
result = await sql_cache.cache_query(
    "SELECT * FROM cached_data",
    strategy=QueryCacheStrategy.CACHE_ONLY
)
```

### SQL Cache Invalidation

```python
# Invalidate specific query
await sql_cache.invalidate_query(
    "SELECT * FROM users WHERE id = %s",
    params={"id": 123}
)

# Invalidate by pattern
await sql_cache.invalidate_pattern("*users*")

# Invalidate by table
await sql_cache.invalidate_table("users")
```

## Cache Strategies

### Write Strategies

#### 1. Write-Through

```python
from ncm_foundation.core.cache import CacheStrategies

strategies = CacheStrategies(redis_cache)

# Write to cache and persistent storage
await strategies.write_through(
    "user:123",
    user_data,
    ttl=3600,
    persistent_store=save_to_database
)
```

#### 2. Write-Behind

```python
# Write to cache immediately, persist in background
await strategies.write_behind(
    "user:123",
    user_data,
    ttl=3600,
    persistent_store=save_to_database,
    delay=5.0  # 5 second delay
)
```

#### 3. Write-Around

```python
# Write to persistent storage, skip cache
await strategies.write_around(
    "user:123",
    user_data,
    persistent_store=save_to_database
)
```

### Invalidation Strategies

#### 1. Time-Based Invalidation

```python
# Automatic expiration
await strategies.time_based_invalidation(
    "user:123",
    ttl=3600,
    callback=cleanup_callback
)
```

#### 2. Event-Based Invalidation

```python
# Invalidate on events
await strategies.event_based_invalidation(
    "user_updated",
    keys=["user:123", "user:456"],
    callback=invalidation_callback
)

# Trigger invalidation
await strategies.trigger_event_invalidation("user_updated")
```

#### 3. Pattern-Based Invalidation

```python
# Invalidate by pattern
await strategies.pattern_based_invalidation(
    "user:*",
    callback=pattern_callback
)
```

#### 4. Dependency-Based Invalidation

```python
# Set up dependencies
await strategies.dependency_based_invalidation(
    "user:123",
    dependencies=["profile:123", "settings:123"]
)

# Invalidate dependencies
await strategies.invalidate_dependencies("profile:123")
```

## Cache Loaders

### Basic Cache Loading

```python
from ncm_foundation.core.cache import CacheLoader

loader = CacheLoader(redis_cache)

# Register loader
async def load_user_data(user_id: int):
    # Load from database
    return await database.get_user(user_id)

loader.register_loader(
    "user_data",
    load_user_data,
    ttl=3600,
    strategy=CacheStrategy.CACHE_ASIDE
)

# Use loader
user_data = await loader.load("user_data", user_id=123)
```

### Cache Loader Decorators

#### 1. Function Decorator

```python
@loader.cache_loader(ttl=3600, strategy=CacheStrategy.READ_THROUGH)
async def get_user_profile(user_id: int):
    return await database.get_user_profile(user_id)

# Function automatically cached
profile = await get_user_profile(123)
```

#### 2. Method Decorator

```python
class UserService:
    @loader.cache_method(ttl=1800, strategy=CacheStrategy.CACHE_ASIDE)
    async def get_user_by_email(self, email: str):
        return await database.get_user_by_email(email)

# Method automatically cached
user = await user_service.get_user_by_email("john@example.com")
```

### Cache Warming

```python
# Warm cache with predefined data
warming_config = [
    {
        "name": "user_data",
        "args": [123],
        "kwargs": {}
    },
    {
        "name": "user_data",
        "args": [456],
        "kwargs": {}
    }
]

results = await loader.warm_cache(warming_config, concurrency=5)
```

### Background Cache Warming

```python
# Start background warming
await loader.start_background_warming(
    warming_config,
    interval=3600,  # 1 hour
    concurrency=5
)

# Stop background warming
await loader.stop_background_warming()
```

## Performance Monitoring

### Cache Statistics

```python
# Get Redis cache stats
stats = cache.get_stats()
print(f"Hit rate: {stats['hit_rate']:.2%}")
print(f"Total requests: {stats['total_requests']}")

# Get SQL cache stats
sql_stats = sql_cache.get_performance_stats()
print(f"Query hit rate: {sql_stats['hit_rate']:.2%}")

# Get loader stats
loader_stats = loader.get_loader_stats()
print(f"Loader hit rate: {loader_stats['overall_hit_rate']:.2%}")
```

### Health Monitoring

```python
# Check cache health
is_healthy = await cache.health_check()
print(f"Cache healthy: {is_healthy}")

# Get loader health
health = loader.get_health_status()
print(f"Loader healthy: {health['is_healthy']}")
```

## Configuration

### Redis Configuration

```python
cache = RedisCache(
    host="localhost",
    port=6379,
    db=0,
    password="your_password",
    max_connections=20,
    retry_on_timeout=True,
    socket_keepalive=True,
    health_check_interval=30,
    key_prefix="ncm:",
    default_ttl=3600,
    serialization=SerializationType.JSON,
    compression=True,
    strategy=CacheStrategy.CACHE_ASIDE
)
```

### SQL Cache Configuration

```python
sql_cache = SQLCache(
    redis_cache,
    default_ttl=1800,
    max_query_size=1024 * 1024,  # 1MB
    enable_query_logging=True,
    enable_performance_monitoring=True
)
```

### Cache Loader Configuration

```python
loader = CacheLoader(
    redis_cache,
    default_ttl=3600,
    enable_metrics=True,
    enable_logging=True
)
```

## Advanced Features

### Multi-Level Caching

```python
from ncm_foundation.core.cache import RedisSyncCache, MultiLevelCache, CacheLevel

# Create L2 cache
l2_cache = RedisSyncCache(host="localhost", port=6379, db=0)

# Create multi-level cache
multi_cache = MultiLevelCache(
    l2_cache=l2_cache,
    l1_max_size=1000,
    l1_default_ttl=300,
    l2_default_ttl=3600,
    enable_promotion=True,
    enable_stampede_prevention=True,
    promotion_threshold=2
)

# Use with loader
async def load_user(user_id: int):
    # Load from database
    return await database.get_user(user_id)

user = await multi_cache.get("user:123", loader=lambda: load_user(123))

# Set in specific level
await multi_cache.set("user:456", user_data, level=CacheLevel.L1)
await multi_cache.set("user:789", user_data, level=CacheLevel.L2)
```

### Serialization Options

```python
from ncm_foundation.core.cache import SerializerFactory, SerializationType, CompressionType

# JSON serialization with compression
json_serializer = SerializerFactory.create_serializer(
    SerializationType.JSON,
    compression_type=CompressionType.GZIP,
    compression_level=6
)

# Pickle serialization
pickle_serializer = SerializerFactory.create_serializer(
    SerializationType.PICKLE
)

# MessagePack serialization with LZ4 compression
msgpack_serializer = SerializerFactory.create_serializer(
    SerializationType.MSGPACK,
    compression_type=CompressionType.LZ4
)

# ORJSON serialization (faster than standard JSON)
orjson_serializer = SerializerFactory.create_serializer(
    SerializationType.ORJSON,
    compression_type=CompressionType.ZSTD
)
```

### Cache Reloading

```python
from ncm_foundation.core.cache import CacheReloader, ReloadStrategy

# Create cache reloader
reloader = CacheReloader(cache)

# Define loader function
async def load_fresh_data():
    return {"timestamp": datetime.utcnow().isoformat(), "data": "Fresh data"}

# Register loader
reloader.register_loader(
    "fresh_data",
    load_fresh_data,
    ttl=300,
    strategy=ReloadStrategy.LAZY
)

# Add reload callback
def reload_callback(key: str, value: Any):
    print(f"Reloaded {key}: {value}")

reloader.add_reload_callback("fresh_data", reload_callback)

# Schedule periodic reload
await reloader.schedule_reload(
    "fresh_data",
    interval=60,  # Reload every minute
    loader=load_fresh_data
)

# Manual reload
await reloader.reload_key("fresh_data", force=True)
```

### Compression

```python
# Enable compression for large values
cache = RedisCache(compression=True)
```

### Connection Pooling

```python
# Configure connection pool
cache = RedisCache(
    max_connections=50,
    retry_on_timeout=True,
    socket_keepalive=True,
    socket_keepalive_options={
        "TCP_KEEPIDLE": 1,
        "TCP_KEEPINTVL": 3,
        "TCP_KEEPCNT": 5
    }
)
```

### TTL Management

```python
# Get TTL for key
ttl = await cache.get_ttl("user:123")

# Extend TTL
await cache.extend_ttl("user:123", 7200)  # 2 hours
```

### Batch Operations

```python
# Get multiple values
values = await cache.get_many(["user:123", "user:456", "user:789"])

# Set multiple values
await cache.set_many({
    "user:123": user_data_1,
    "user:456": user_data_2,
    "user:789": user_data_3
}, ttl=3600)

# Use pipeline for batch operations
pipeline = await cache.pipeline()
pipeline.set("key1", "value1")
pipeline.set("key2", "value2")
pipeline.set("key3", "value3")
results = await cache.execute_pipeline(pipeline)
```

## Best Practices

### 1. Cache Key Design

```python
# Use consistent key patterns
user_key = f"user:{user_id}"
profile_key = f"profile:{user_id}"
settings_key = f"settings:{user_id}"

# Use namespaces
cache_key = f"ncm:users:{user_id}"
```

### 2. TTL Strategy

```python
# Different TTLs for different data types
user_data_ttl = 3600      # 1 hour
profile_data_ttl = 1800   # 30 minutes
settings_ttl = 7200       # 2 hours
```

### 3. Cache Invalidation

```python
# Invalidate related data
async def update_user(user_id: int, data: dict):
    # Update database
    await database.update_user(user_id, data)

    # Invalidate related cache entries
    await cache.delete(f"user:{user_id}")
    await cache.delete(f"profile:{user_id}")
    await cache.clear_pattern(f"user:{user_id}:*")
```

### 4. Error Handling

```python
async def safe_cache_get(key: str, fallback_func: callable):
    try:
        value = await cache.get(key)
        if value is not None:
            return value
    except Exception as e:
        logger.error(f"Cache get failed for key {key}: {e}")

    # Fallback to source
    return await fallback_func()
```

### 5. Monitoring and Alerting

```python
# Monitor cache performance
async def monitor_cache_performance():
    stats = cache.get_stats()

    if stats['hit_rate'] < 0.8:  # 80% hit rate threshold
        logger.warning(f"Low cache hit rate: {stats['hit_rate']:.2%}")

    if stats['errors'] > 100:  # Error threshold
        logger.error(f"High cache error count: {stats['errors']}")
```

## Examples

### Complete Example

```python
import asyncio
from ncm_foundation.core.cache import (
    RedisCache, SQLCache, CacheLoader, CacheStrategy
)

async def main():
    # Initialize cache
    cache = RedisCache(
        host="localhost",
        port=6379,
        default_ttl=3600,
        strategy=CacheStrategy.CACHE_ASIDE
    )

    # Initialize SQL cache
    sql_cache = SQLCache(cache)

    # Initialize cache loader
    loader = CacheLoader(cache)

    # Register loader
    async def load_user(user_id: int):
        # Simulate database query
        await asyncio.sleep(0.1)
        return {"id": user_id, "name": f"User {user_id}"}

    loader.register_loader("user", load_user, ttl=1800)

    # Use cache
    user = await loader.load("user", user_id=123)
    print(f"Loaded user: {user}")

    # Cache SQL query
    result = await sql_cache.cache_query(
        "SELECT * FROM users WHERE id = %s",
        params={"id": 123},
        strategy=QueryCacheStrategy.CACHE_FIRST
    )
    print(f"SQL result: {result}")

    # Get statistics
    stats = cache.get_stats()
    print(f"Cache hit rate: {stats['hit_rate']:.2%}")

    # Close cache
    await cache.close()

# Run example
asyncio.run(main())
```

### Microservice Integration

```python
from fastapi import FastAPI
from ncm_foundation.core.cache import RedisCache, CacheLoader

app = FastAPI()
cache = RedisCache(host="redis", port=6379)
loader = CacheLoader(cache)

# Register loaders
loader.register_loader("user", load_user_from_db)
loader.register_loader("products", load_products_from_db)

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    return await loader.load("user", user_id=user_id)

@app.get("/products")
async def get_products():
    return await loader.load("products")
```

## Troubleshooting

### Common Issues

1. **Connection Errors**

   ```python
   # Check Redis connection
   is_healthy = await cache.health_check()
   if not is_healthy:
       logger.error("Redis connection failed")
   ```

2. **High Memory Usage**

   ```python
   # Monitor cache size
   stats = cache.get_stats()
   if stats['memory_usage'] > threshold:
       logger.warning("High cache memory usage")
   ```

3. **Low Hit Rate**
   ```python
   # Check hit rate
   stats = cache.get_stats()
   if stats['hit_rate'] < 0.5:
       logger.warning("Low cache hit rate")
   ```

### Performance Optimization

1. **Use Appropriate TTLs**
2. **Implement Cache Warming**
3. **Monitor Performance Metrics**
4. **Use Batch Operations**
5. **Implement Proper Invalidation**

## Support

For questions, issues, or contributions:

1. Check the troubleshooting section
2. Review the examples
3. Create an issue in the repository
4. Check the main project documentation

## License

This caching system is part of the ncm-foundation project and follows the same license terms.
