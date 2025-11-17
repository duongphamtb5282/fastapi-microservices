"""Test cases for circuit breaker messaging component."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from ncm_foundation.core.messaging.circuit_breaker import CircuitBreaker


class TestCircuitBreaker:
    """Test CircuitBreaker functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=1
        )

    @pytest.mark.asyncio
    async def test_circuit_breaker_initial_state(self):
        """Test circuit breaker initial state."""
        assert self.circuit_breaker.failure_count == 0
        assert self.circuit_breaker.state == "CLOSED"

    @pytest.mark.asyncio
    async def test_successful_call(self):
        """Test successful function call."""
        async def successful_func():
            return "success"

        result = await self.circuit_breaker.call(successful_func)
        assert result == "success"
        assert self.circuit_breaker.failure_count == 0
        assert self.circuit_breaker.state == "CLOSED"

    @pytest.mark.asyncio
    async def test_failure_threshold(self):
        """Test circuit breaker opens after failure threshold."""
        async def failing_func():
            raise Exception("Test failure")

        # Call failing function multiple times
        for i in range(3):
            with pytest.raises(Exception):
                await self.circuit_breaker.call(failing_func)

        assert self.circuit_breaker.failure_count == 3
        assert self.circuit_breaker.state == "OPEN"

    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovery after timeout."""
        async def failing_func():
            raise Exception("Test failure")

        # Trigger circuit breaker to open
        for i in range(3):
            with pytest.raises(Exception):
                await self.circuit_breaker.call(failing_func)

        assert self.circuit_breaker.state == "OPEN"

        # Wait for recovery timeout
        await asyncio.sleep(1.1)

        # Circuit should be half-open now
        assert self.circuit_breaker.state == "HALF_OPEN"

        # Successful call should close the circuit
        async def successful_func():
            return "success"

        result = await self.circuit_breaker.call(successful_func)
        assert result == "success"
        assert self.circuit_breaker.state == "CLOSED"

    @pytest.mark.asyncio
    async def test_circuit_breaker_failure_after_recovery(self):
        """Test circuit breaker opens again after recovery failure."""
        async def failing_func():
            raise Exception("Test failure")

        # Trigger circuit breaker to open
        for i in range(3):
            with pytest.raises(Exception):
                await self.circuit_breaker.call(failing_func)

        assert self.circuit_breaker.state == "OPEN"

        # Wait for recovery timeout
        await asyncio.sleep(1.1)

        # Half-open state
        assert self.circuit_breaker.state == "HALF_OPEN"

        # Failure in half-open should open circuit again
        with pytest.raises(Exception):
            await self.circuit_breaker.call(failing_func)

        assert self.circuit_breaker.state == "OPEN"
