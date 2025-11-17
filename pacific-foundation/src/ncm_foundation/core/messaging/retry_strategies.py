"""
Retry strategies for message processing.
"""

import asyncio
import random
from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable, Optional

from ncm_foundation.core.logging import logger


class RetryStrategy(ABC):
    """Abstract base class for retry strategies."""

    @abstractmethod
    async def execute_with_retry(
        self, func: Callable[..., Awaitable[Any]], *args, **kwargs
    ) -> Any:
        """Execute a function with retry logic."""
        pass


class ExponentialBackoffStrategy(RetryStrategy):
    """Exponential backoff retry strategy."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        jitter: bool = True,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter
        logger.info(
            "ExponentialBackoffStrategy initialized",
            max_retries=max_retries,
            base_delay=base_delay,
        )

    async def execute_with_retry(
        self, func: Callable[..., Awaitable[Any]], *args, **kwargs
    ) -> Any:
        """Execute a function with exponential backoff retry."""
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt == self.max_retries:
                    logger.error("Max retries exceeded", attempt=attempt, error=str(e))
                    raise e

                delay = min(self.base_delay * (2**attempt), self.max_delay)
                if self.jitter:
                    delay *= 0.5 + random.random() * 0.5  # Add jitter between 50-100%

                logger.warning(
                    "Retry attempt failed, retrying",
                    attempt=attempt + 1,
                    delay=delay,
                    error=str(e),
                )
                await asyncio.sleep(delay)

        raise last_exception


class LinearBackoffStrategy(RetryStrategy):
    """Linear backoff retry strategy."""

    def __init__(self, max_retries: int = 3, delay: float = 1.0, jitter: bool = True):
        self.max_retries = max_retries
        self.delay = delay
        self.jitter = jitter
        logger.info(
            "LinearBackoffStrategy initialized", max_retries=max_retries, delay=delay
        )

    async def execute_with_retry(
        self, func: Callable[..., Awaitable[Any]], *args, **kwargs
    ) -> Any:
        """Execute a function with linear backoff retry."""
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt == self.max_retries:
                    logger.error("Max retries exceeded", attempt=attempt, error=str(e))
                    raise e

                delay = self.delay
                if self.jitter:
                    delay *= 0.5 + random.random() * 0.5  # Add jitter between 50-100%

                logger.warning(
                    "Retry attempt failed, retrying",
                    attempt=attempt + 1,
                    delay=delay,
                    error=str(e),
                )
                await asyncio.sleep(delay)

        raise last_exception
