"""Structured logging with correlation ID support."""

import json
import logging
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Dict, Optional

# Context variable for storing correlation ID
correlation_id_var: ContextVar[Optional[str]] = ContextVar(
    "correlation_id", default=None
)

logger = logging.getLogger(__name__)


class CorrelationIDFormatter(logging.Formatter):
    """Custom formatter that includes correlation ID in log records."""

    def format(self, record: logging.LogRecord) -> str:
        # Add correlation ID to log record
        correlation_id = correlation_id_var.get()
        if correlation_id:
            record.correlation_id = correlation_id
        else:
            record.correlation_id = "no-correlation-id"

        return super().format(record)


class JSONCorrelationFormatter(logging.Formatter):
    """JSON formatter that includes correlation ID and structured data."""

    def format(self, record: logging.LogRecord) -> str:
        # Get correlation ID from context
        correlation_id = correlation_id_var.get()

        # Build log entry
        log_entry = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id or "no-correlation-id",
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "getMessage",
                "exc_info",
                "exc_text",
                "stack_info",
                "correlation_id",
            }:
                log_entry[key] = value

        return json.dumps(log_entry, default=str)


def setup_logging(log_level: str = "INFO", log_format: str = "json"):
    """Setup logging configuration."""
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    console_handler = logging.StreamHandler()

    # Set formatter based on format type
    if log_format.lower() == "json":
        formatter = JSONCorrelationFormatter()
    else:
        formatter = CorrelationIDFormatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(correlation_id)s - %(message)s"
        )

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Configure specific loggers
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Get logger with correlation ID support."""
    return logging.getLogger(name)


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID in context."""
    correlation_id_var.set(correlation_id)


def get_correlation_id() -> Optional[str]:
    """Get correlation ID from context."""
    return correlation_id_var.get()
