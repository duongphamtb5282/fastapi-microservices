"""Test cases for core decorators."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from ncm_foundation.core.config import Settings
from ncm_sample.core.decorators import (
    log_method_call,
    cache_result,
    with_transaction,
    with_session_transaction
)


class TestDecorators:
    """Test decorator functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.settings = Settings()

    def test_log_method_call_decorator(self):
        """Test log_method_call decorator."""
        @log_method_call
        def test_function():
            return "test_result"

        # Should not raise any errors
        result = test_function()
        assert result == "test_result"

    @pytest.mark.asyncio
    async def test_log_method_call_async(self):
        """Test log_method_call decorator with async functions."""
        @log_method_call
        async def async_test_function():
            return "async_result"

        result = await async_test_function()
        assert result == "async_result"

    @pytest.mark.asyncio
    async def test_cache_result_decorator(self):
        """Test cache_result decorator."""
        call_count = 0

        @cache_result(ttl=300, key_prefix="test")
        async def cached_function(value):
            nonlocal call_count
            call_count += 1
            return f"result_{value}_{call_count}"

        # First call should execute the function
        result1 = await cached_function("test1")
        assert call_count == 1
        assert "result_test1_1" in result1

        # Second call with same parameters should use cache
        result2 = await cached_function("test1")
        assert call_count == 1  # Should not increment
        assert result1 == result2

        # Different parameters should execute the function again
        result3 = await cached_function("test2")
        assert call_count == 2
        assert "result_test2_2" in result3

    def test_with_transaction_decorator_no_manager(self):
        """Test with_transaction decorator when no transaction manager is available."""
        @with_transaction
        def simple_function():
            return "no_transaction"

        result = simple_function()
        assert result == "no_transaction"

    @pytest.mark.asyncio
    async def test_with_session_transaction_decorator(self):
        """Test with_session_transaction decorator."""
        @with_session_transaction
        async def function_with_transaction():
            return "transaction_result"

        result = await function_with_transaction()
        assert result == "transaction_result"

    def test_decorator_stacking(self):
        """Test that decorators can be stacked."""
        @with_transaction
        @log_method_call
        def stacked_function():
            return "stacked"

        result = stacked_function()
        assert result == "stacked"
