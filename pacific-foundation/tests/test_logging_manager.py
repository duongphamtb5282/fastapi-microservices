"""Test cases for logging manager."""

import pytest
import logging
from unittest.mock import patch, MagicMock

from ncm_foundation.core.logging.manager import LogManager, LogConfig, LogLevel
from ncm_foundation.core.logging import get_logger, set_correlation_id


class TestLogManager:
    """Test LogManager functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.log_config = LogConfig(
            level=LogLevel.INFO,
            format="json",
            handlers=["console"],
            enable_rotation=False,
            enable_masking=False
        )

    def test_log_manager_initialization(self):
        """Test LogManager can be initialized."""
        log_manager = LogManager(self.log_config)
        assert log_manager.config == self.log_config
        assert log_manager._running is False

    def test_log_config_creation(self):
        """Test LogConfig creation."""
        config = LogConfig()
        assert config.level == LogLevel.INFO
        assert config.format == "json"
        assert config.handlers == ["console"]

    def test_log_level_enum(self):
        """Test LogLevel enum values."""
        assert LogLevel.DEBUG.value == "DEBUG"
        assert LogLevel.INFO.value == "INFO"
        assert LogLevel.WARNING.value == "WARNING"
        assert LogLevel.ERROR.value == "ERROR"

    @pytest.mark.asyncio
    async def test_log_manager_start_stop(self):
        """Test starting and stopping the log manager."""
        log_manager = LogManager(self.log_config)

        # Should start without errors
        await log_manager.start()
        assert log_manager._running is True

        # Should stop without errors
        await log_manager.stop()
        assert log_manager._running is False

    def test_get_logger_function(self):
        """Test get_logger utility function."""
        logger = get_logger("test_module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"

    def test_correlation_id_functionality(self):
        """Test correlation ID functionality."""
        # Set correlation ID
        test_id = "test-correlation-123"
        set_correlation_id(test_id)

        # Get correlation ID from context
        from ncm_foundation.core.logging.manager import correlation_id_var
        assert correlation_id_var.get() == test_id

        # Reset correlation ID
        set_correlation_id(None)
        assert correlation_id_var.get() is None
