"""
Logging system with structured logging, rotation, and masking.
"""

from .formatters import CorrelationIDFormatter, JSONFormatter, StructuredFormatter
from .handlers import ConsoleHandler, ElasticsearchHandler, FileHandler
from .interfaces import LogConfig, LogFormatter, LogHandler, LogLevel
from .manager import (
    LogManager,
    get_correlation_id,
    get_logger,
    get_request_id,
    get_service_name,
    get_user_id,
    logger,
    set_correlation_id,
    set_request_id,
    set_service_name,
    set_user_id,
    setup_logging,
)
from .masking import LogMasker, SensitiveDataMasker
from .rotation import LogRotator, SizeBasedRotator, TimeBasedRotator

__all__ = [
    "LogHandler",
    "LogFormatter",
    "LogConfig",
    "LogLevel",
    "FileHandler",
    "ConsoleHandler",
    "ElasticsearchHandler",
    "JSONFormatter",
    "StructuredFormatter",
    "CorrelationIDFormatter",
    "LogRotator",
    "SizeBasedRotator",
    "TimeBasedRotator",
    "LogMasker",
    "SensitiveDataMasker",
    "LogManager",
    "get_logger",
    "setup_logging",
    "logger",
    "set_correlation_id",
    "get_correlation_id",
    "set_request_id",
    "get_request_id",
    "set_user_id",
    "get_user_id",
    "set_service_name",
    "get_service_name",
]
