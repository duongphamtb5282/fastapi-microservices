"""
Log formatters implementation.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict

from .interfaces import LogFormatter, LogRecord


class JSONFormatter(LogFormatter):
    """JSON log formatter."""

    def __init__(self, include_extra: bool = True):
        self.include_extra = include_extra

    def format(self, record: LogRecord) -> str:
        """Format log record as JSON."""
        log_entry = {
            "timestamp": record.timestamp.isoformat(),
            "level": record.level.value,
            "logger": record.logger_name,
            "message": record.message,
            "correlation_id": record.correlation_id,
            "request_id": record.request_id,
            "user_id": record.user_id,
            "service_name": record.service_name,
        }

        if self.include_extra and record.extra:
            log_entry["extra"] = record.extra

        if record.exc_info:
            log_entry["exception"] = self.format_exception(record.exc_info)

        return json.dumps(log_entry, default=str)

    def format_exception(self, exc_info: Any) -> str:
        """Format exception information."""
        return logging.Formatter().formatException(exc_info)


class StructuredFormatter(LogFormatter):
    """Structured log formatter."""

    def __init__(self, template: str = None):
        self.template = template or (
            "{timestamp} | {level:8} | {logger:20} | {correlation_id:36} | {message}"
        )

    def format(self, record: LogRecord) -> str:
        """Format log record with structure."""
        return self.template.format(
            timestamp=record.timestamp.isoformat(),
            level=record.level.value,
            logger=record.logger_name,
            correlation_id=record.correlation_id or "N/A",
            request_id=record.request_id or "N/A",
            user_id=record.user_id or "N/A",
            service_name=record.service_name or "N/A",
            message=record.message,
        )

    def format_exception(self, exc_info: Any) -> str:
        """Format exception information."""
        return logging.Formatter().formatException(exc_info)


class CorrelationIDFormatter(LogFormatter):
    """Correlation ID formatter."""

    def __init__(self, include_context: bool = True):
        self.include_context = include_context

    def format(self, record: LogRecord) -> str:
        """Format log record with correlation ID."""
        parts = [
            f"[{record.timestamp.isoformat()}]",
            f"[{record.level.value}]",
            f"[{record.logger_name}]",
        ]

        if record.correlation_id:
            parts.append(f"[corr:{record.correlation_id}]")

        if record.request_id:
            parts.append(f"[req:{record.request_id}]")

        if record.user_id:
            parts.append(f"[user:{record.user_id}]")

        if record.service_name:
            parts.append(f"[svc:{record.service_name}]")

        parts.append(record.message)

        if record.exc_info:
            parts.append(f"\n{self.format_exception(record.exc_info)}")

        return " ".join(parts)

    def format_exception(self, exc_info: Any) -> str:
        """Format exception information."""
        return logging.Formatter().formatException(exc_info)
