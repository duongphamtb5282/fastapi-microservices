"""Pytest configuration and fixtures."""

import asyncio
import pytest
from unittest.mock import MagicMock

from ncm_foundation.core.config import Settings


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = Settings()
    return settings


@pytest.fixture
def mock_database_manager():
    """Mock database manager for testing."""
    db_manager = MagicMock()
    db_manager.get_session = MagicMock()
    db_manager.get_transaction_manager = MagicMock()
    db_manager.health_check = MagicMock(return_value=True)
    return db_manager


@pytest.fixture
def mock_cache_manager():
    """Mock cache manager for testing."""
    cache_manager = MagicMock()
    cache_manager.set = MagicMock()
    cache_manager.get = MagicMock()
    cache_manager.invalidate = MagicMock()
    cache_manager.invalidate_pattern = MagicMock()
    cache_manager.health_check = MagicMock(return_value=True)
    cache_manager.get_stats = MagicMock(return_value={"hits": 0, "misses": 0})
    return cache_manager


@pytest.fixture
def mock_logger():
    """Mock logger for testing."""
    logger = MagicMock()
    return logger
