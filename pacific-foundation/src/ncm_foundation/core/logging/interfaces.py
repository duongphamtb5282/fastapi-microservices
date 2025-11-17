"""
Logging system interfaces and abstractions.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class LogLevel(Enum):
    """Log level enumeration."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogConfig:
    """Logging configuration."""

    def __init__(
        self,
        level: LogLevel = LogLevel.INFO,
        format: str = "json",  # json, text, structured
        handlers: List[str] = None,  # file, console, elasticsearch
        file_path: str = "logs/app.log",
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        max_files: int = 5,
        rotation_interval: str = "daily",  # daily, weekly, monthly
        enable_rotation: bool = True,
        enable_masking: bool = True,
        elasticsearch_url: Optional[str] = None,
        elasticsearch_index: str = "logs",
        correlation_id_header: str = "X-Correlation-ID",
        request_id_header: str = "X-Request-ID",
    ):
        self.level = level
        self.format = format
        self.handlers = handlers or ["console"]
        self.file_path = file_path
        self.max_file_size = max_file_size
        self.max_files = max_files
        self.rotation_interval = rotation_interval
        self.enable_rotation = enable_rotation
        self.enable_masking = enable_masking
        self.elasticsearch_url = elasticsearch_url
        self.elasticsearch_index = elasticsearch_index
        self.correlation_id_header = correlation_id_header
        self.request_id_header = request_id_header


class LogHandler(ABC):
    """Abstract log handler interface."""

    @abstractmethod
    async def emit(self, record: Any) -> None:
        """Emit log record."""
        pass

    @abstractmethod
    async def flush(self) -> None:
        """Flush handler buffer."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close handler."""
        pass


class LogFormatter(ABC):
    """Abstract log formatter interface."""

    @abstractmethod
    def format(self, record: Any) -> str:
        """Format log record."""
        pass

    @abstractmethod
    def format_exception(self, exc_info: Any) -> str:
        """Format exception information."""
        pass


class LogRotator(ABC):
    """Abstract log rotator interface."""

    @abstractmethod
    async def should_rotate(self, file_path: str) -> bool:
        """Check if log file should be rotated."""
        pass

    @abstractmethod
    async def rotate(self, file_path: str) -> str:
        """Rotate log file and return new file path."""
        pass

    @abstractmethod
    async def cleanup_old_files(self, file_path: str, max_files: int) -> None:
        """Clean up old log files."""
        pass


class LogMasker(ABC):
    """Abstract log masker interface."""

    @abstractmethod
    def mask_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mask sensitive data in dictionary."""
        pass

    @abstractmethod
    def mask_text(self, text: str) -> str:
        """Mask sensitive data in text."""
        pass

    @abstractmethod
    def add_pattern(self, pattern: str, replacement: str) -> None:
        """Add masking pattern."""
        pass

    @abstractmethod
    def remove_pattern(self, pattern: str) -> None:
        """Remove masking pattern."""
        pass


class LogRecord:
    """Enhanced log record with additional fields."""

    def __init__(
        self,
        level: LogLevel,
        message: str,
        logger_name: str,
        timestamp: Optional[datetime] = None,
        correlation_id: Optional[str] = None,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        service_name: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
        exc_info: Optional[Any] = None,
    ):
        self.level = level
        self.message = message
        self.logger_name = logger_name
        self.timestamp = timestamp or datetime.utcnow()
        self.correlation_id = correlation_id
        self.request_id = request_id
        self.user_id = user_id
        self.service_name = service_name
        self.extra = extra or {}
        self.exc_info = exc_info

    def to_dict(self) -> Dict[str, Any]:
        """Convert record to dictionary."""
        return {
            "level": self.level.value,
            "message": self.message,
            "logger": self.logger_name,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "request_id": self.request_id,
            "user_id": self.user_id,
            "service_name": self.service_name,
            "extra": self.extra,
            "exc_info": self.exc_info,
        }
