"""Test cases for cache manager."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ncm_foundation.core.cache.manager import CacheManager
from ncm_foundation.core.cache.serializers import SerializationType


class TestCacheManager:
    """Test CacheManager functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.cache_config = {
            "redis_url": "redis://localhost:6379/0",
            "default_ttl": 300,
            "max_connections": 10,
            "serialization_type": "json"
        }

    @pytest.mark.asyncio
    async def test_cache_manager_initialization(self):
        """Test CacheManager can be initialized."""
        with patch('ncm_foundation.core.cache.redis_cache.RedisCache') as mock_redis:
            mock_redis_instance = MagicMock()
            mock_redis_instance.connect = AsyncMock()
            mock_redis_instance.health_check = AsyncMock(return_value=True)
            mock_redis.return_value = mock_redis_instance

            cache_manager = CacheManager()

            assert cache_manager is not None
            assert hasattr(cache_manager, 'cache')
            assert hasattr(cache_manager, 'health_check')

    @pytest.mark.asyncio
    async def test_cache_set_and_get(self):
        """Test basic cache operations."""
        with patch('ncm_foundation.core.cache.redis_cache.RedisCache') as mock_redis:
            mock_redis_instance = MagicMock()
            mock_redis_instance.connect = AsyncMock()
            mock_redis_instance.set = AsyncMock()
            mock_redis_instance.get = AsyncMock(return_value="cached_value")
            mock_redis_instance.health_check = AsyncMock(return_value=True)
            mock_redis.return_value = mock_redis_instance

            cache_manager = CacheManager()

            # Test set operation
            await cache_manager.set("test_key", "test_value", expire=300)
            mock_redis_instance.set.assert_called_once()

            # Test get operation
            result = await cache_manager.get("test_key")
            assert result == "cached_value"
            mock_redis_instance.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_invalidate(self):
        """Test cache invalidation."""
        with patch('ncm_foundation.core.cache.redis_cache.RedisCache') as mock_redis:
            mock_redis_instance = MagicMock()
            mock_redis_instance.connect = AsyncMock()
            mock_redis_instance.invalidate = AsyncMock()
            mock_redis_instance.invalidate_pattern = AsyncMock()
            mock_redis_instance.health_check = AsyncMock(return_value=True)
            mock_redis.return_value = mock_redis_instance

            cache_manager = CacheManager()

            # Test single key invalidation
            await cache_manager.invalidate("test_key")
            mock_redis_instance.invalidate.assert_called_once_with("test_key")

            # Test pattern invalidation
            await cache_manager.invalidate_pattern("test_*")
            mock_redis_instance.invalidate_pattern.assert_called_once_with("test_*")

    @pytest.mark.asyncio
    async def test_cache_serialization(self):
        """Test cache serialization."""
        with patch('ncm_foundation.core.cache.redis_cache.RedisCache') as mock_redis:
            mock_redis_instance = MagicMock()
            mock_redis_instance.connect = AsyncMock()
            mock_redis_instance.set = AsyncMock()
            mock_redis_instance.get = AsyncMock(return_value='{"key": "value"}')
            mock_redis_instance.health_check = AsyncMock(return_value=True)
            mock_redis.return_value = mock_redis_instance

            cache_manager = CacheManager()

            # Test setting with serialization
            test_data = {"key": "value"}
            await cache_manager.set("test_key", test_data, expire=300, serialize=True)

            # Test getting with deserialization
            result = await cache_manager.get("test_key", deserialize=True)
            assert result == test_data

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test cache health check."""
        with patch('ncm_foundation.core.cache.redis_cache.RedisCache') as mock_redis:
            mock_redis_instance = MagicMock()
            mock_redis_instance.connect = AsyncMock()
            mock_redis_instance.health_check = AsyncMock(return_value=True)
            mock_redis.return_value = mock_redis_instance

            cache_manager = CacheManager()

            health = await cache_manager.health_check()
            assert health is True

    def test_cache_stats(self):
        """Test cache statistics."""
        with patch('ncm_foundation.core.cache.redis_cache.RedisCache') as mock_redis:
            mock_redis_instance = MagicMock()
            mock_redis_instance.connect = AsyncMock()
            mock_redis_instance.get_stats = MagicMock(return_value={"hits": 10, "misses": 5})
            mock_redis_instance.health_check = AsyncMock(return_value=True)
            mock_redis.return_value = mock_redis_instance

            cache_manager = CacheManager()

            stats = cache_manager.get_stats()
            assert "cache" in stats
            assert stats["cache"]["hits"] == 10
            assert stats["cache"]["misses"] == 5
