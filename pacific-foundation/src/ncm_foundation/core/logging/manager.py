"""
Log manager implementation.
"""

import asyncio
import logging
import sys
from contextvars import ContextVar
from typing import Any, Dict, List, Optional

from .formatters import CorrelationIDFormatter, JSONFormatter, StructuredFormatter
from .handlers import ConsoleHandler, ElasticsearchHandler, FileHandler
from .interfaces import LogConfig, LogLevel, LogRecord
from .masking import LogMasker
from .rotation import LogRotator

# Context variables for correlation and request IDs
correlation_id_var: ContextVar[Optional[str]] = ContextVar(
    "correlation_id", default=None
)
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)
service_name_var: ContextVar[Optional[str]] = ContextVar("service_name", default=None)


class LogManager:
    """Centralized log manager."""

    def __init__(self, config: LogConfig):
        self.config = config
        self._handlers: List[Any] = []
        self._formatters: Dict[str, Any] = {}
        self._rotator: Optional[LogRotator] = None
        self._masker: Optional[LogMasker] = None
        self._running = False
        self._background_tasks: List[asyncio.Task] = []

    async def start(self) -> None:
        """Start log manager."""
        if self._running:
            return

        try:
            # Initialize formatters
            await self._setup_formatters()

            # Initialize handlers
            await self._setup_handlers()

            # Initialize rotator if enabled
            if self.config.enable_rotation:
                await self._setup_rotator()

            # Initialize masker if enabled
            if self.config.enable_masking:
                await self._setup_masker()

            # Start background tasks
            await self._start_background_tasks()

            self._running = True
            logging.info("Log manager started")

        except Exception as e:
            logging.error(f"Failed to start log manager: {e}")
            raise

    async def stop(self) -> None:
        """Stop log manager."""
        if not self._running:
            return

        try:
            # Cancel background tasks
            for task in self._background_tasks:
                task.cancel()

            # Wait for tasks to complete
            if self._background_tasks:
                await asyncio.gather(*self._background_tasks, return_exceptions=True)

            # Close handlers
            for handler in self._handlers:
                await handler.close()

            self._running = False
            logging.info("Log manager stopped")

        except Exception as e:
            logging.error(f"Failed to stop log manager: {e}")

    async def _setup_formatters(self) -> None:
        """Setup log formatters."""
        if self.config.format == "json":
            self._formatters["json"] = JSONFormatter()
        elif self.config.format == "structured":
            self._formatters["structured"] = StructuredFormatter()
        else:
            self._formatters["correlation"] = CorrelationIDFormatter()

    async def _setup_handlers(self) -> None:
        """Setup log handlers."""
        for handler_name in self.config.handlers:
            if handler_name == "file":
                handler = FileHandler(
                    file_path=self.config.file_path,
                    formatter=self._formatters.get("json")
                    or self._formatters.get("structured"),
                )
            elif handler_name == "console":
                handler = ConsoleHandler(
                    formatter=self._formatters.get("correlation")
                    or self._formatters.get("structured")
                )
            elif handler_name == "elasticsearch":
                if self.config.elasticsearch_url:
                    handler = ElasticsearchHandler(
                        url=self.config.elasticsearch_url,
                        index=self.config.elasticsearch_index,
                        formatter=self._formatters.get("json"),
                    )
                else:
                    logging.warning(
                        "Elasticsearch URL not configured, skipping handler"
                    )
                    continue
            else:
                logging.warning(f"Unknown handler: {handler_name}")
                continue

            self._handlers.append(handler)

    async def _setup_rotator(self) -> None:
        """Setup log rotator."""
        from .rotation import SizeBasedRotator, TimeBasedRotator

        if self.config.rotation_interval in ["daily", "weekly", "monthly"]:
            self._rotator = TimeBasedRotator(self.config.rotation_interval)
        else:
            self._rotator = SizeBasedRotator(self.config.max_file_size)

    async def _setup_masker(self) -> None:
        """Setup log masker."""
        from .masking import SensitiveDataMasker

        self._masker = SensitiveDataMasker()

    async def _start_background_tasks(self) -> None:
        """Start background tasks."""
        if self._rotator:
            task = asyncio.create_task(self._rotation_task())
            self._background_tasks.append(task)

    async def _rotation_task(self) -> None:
        """Background log rotation task."""
        while self._running:
            try:
                await asyncio.sleep(3600)  # Check every hour

                if self._rotator and self.config.enable_rotation:
                    for handler in self._handlers:
                        if hasattr(handler, "file_path"):
                            if await self._rotator.should_rotate(handler.file_path):
                                new_path = await self._rotator.rotate(handler.file_path)
                                await self._rotator.cleanup_old_files(
                                    handler.file_path, self.config.max_files
                                )
                                logging.info(f"Log rotated: {new_path}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"Log rotation task error: {e}")

    async def emit_log(self, record: LogRecord) -> None:
        """Emit log record to all handlers."""
        if not self._running:
            return

        try:
            # Apply masking if enabled
            if self._masker:
                record.extra = self._masker.mask_sensitive_data(record.extra)
                record.message = self._masker.mask_text(record.message)

            # Emit to all handlers
            for handler in self._handlers:
                try:
                    await handler.emit(record)
                except Exception as e:
                    logging.error(f"Handler error: {e}")

        except Exception as e:
            logging.error(f"Failed to emit log: {e}")

    async def flush_all(self) -> None:
        """Flush all handlers."""
        for handler in self._handlers:
            try:
                await handler.flush()
            except Exception as e:
                logging.error(f"Failed to flush handler: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get log manager statistics."""
        return {
            "running": self._running,
            "handlers_count": len(self._handlers),
            "background_tasks": len(self._background_tasks),
            "rotation_enabled": self.config.enable_rotation,
            "masking_enabled": self.config.enable_masking,
            "format": self.config.format,
            "level": self.config.level.value,
        }


def get_logger(name: str) -> logging.Logger:
    """Get logger with correlation ID support."""
    logger = logging.getLogger(name)

    # Add correlation ID to log records
    old_factory = logging.getLogRecordFactory()

    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        record.correlation_id = correlation_id_var.get()
        record.request_id = request_id_var.get()
        record.user_id = user_id_var.get()
        record.service_name = service_name_var.get()
        return record

    logging.setLogRecordFactory(record_factory)

    return logger


async def setup_logging(
    level: str = "INFO", format: str = "json", handlers: List[str] = None, **kwargs
) -> LogManager:
    """Setup logging system."""
    log_level = LogLevel(level.upper())
    config = LogConfig(
        level=log_level, format=format, handlers=handlers or ["console"], **kwargs
    )

    manager = LogManager(config)
    await manager.start()

    return manager


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID in context."""
    correlation_id_var.set(correlation_id)


def set_request_id(request_id: str) -> None:
    """Set request ID in context."""
    request_id_var.set(request_id)


def set_user_id(user_id: str) -> None:
    """Set user ID in context."""
    user_id_var.set(user_id)


def set_service_name(service_name: str) -> None:
    """Set service name in context."""
    service_name_var.set(service_name)


def get_correlation_id() -> Optional[str]:
    """Get correlation ID from context."""
    return correlation_id_var.get()


def get_request_id() -> Optional[str]:
    """Get request ID from context."""
    return request_id_var.get()


def get_user_id() -> Optional[str]:
    """Get user ID from context."""
    return user_id_var.get()


def get_service_name() -> Optional[str]:
    """Get service name from context."""
    return service_name_var.get()


# Default logger instance
logger = get_logger(__name__)
