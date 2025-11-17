"""
Log handlers implementation.
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Optional

from .interfaces import LogHandler, LogRecord


class FileHandler(LogHandler):
    """File log handler."""

    def __init__(self, file_path: str, formatter: Any = None):
        self.file_path = file_path
        self.formatter = formatter
        self._file = None
        self._lock = asyncio.Lock()

    async def emit(self, record: LogRecord) -> None:
        """Emit log record to file."""
        async with self._lock:
            try:
                if not self._file:
                    # Ensure directory exists
                    os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
                    self._file = open(self.file_path, "a", encoding="utf-8")

                formatted_record = (
                    self.formatter.format(record) if self.formatter else str(record)
                )
                self._file.write(formatted_record + "\n")

            except Exception as e:
                logging.error(f"File handler error: {e}")

    async def flush(self) -> None:
        """Flush file buffer."""
        if self._file:
            self._file.flush()

    async def close(self) -> None:
        """Close file handler."""
        if self._file:
            self._file.close()
            self._file = None


class ConsoleHandler(LogHandler):
    """Console log handler."""

    def __init__(self, formatter: Any = None):
        self.formatter = formatter

    async def emit(self, record: LogRecord) -> None:
        """Emit log record to console."""
        try:
            formatted_record = (
                self.formatter.format(record) if self.formatter else str(record)
            )
            print(formatted_record)

        except Exception as e:
            logging.error(f"Console handler error: {e}")

    async def flush(self) -> None:
        """Flush console buffer."""
        sys.stdout.flush()

    async def close(self) -> None:
        """Close console handler."""
        pass


class ElasticsearchHandler(LogHandler):
    """Elasticsearch log handler."""

    def __init__(self, url: str, index: str, formatter: Any = None):
        self.url = url
        self.index = index
        self.formatter = formatter
        self._client = None
        self._buffer: list = []
        self._buffer_size = 100
        self._flush_interval = 30  # seconds
        self._last_flush = datetime.utcnow()

    async def _get_client(self):
        """Get Elasticsearch client."""
        if not self._client:
            try:
                from elasticsearch import AsyncElasticsearch

                self._client = AsyncElasticsearch([self.url])
            except ImportError:
                logging.error("Elasticsearch client not available")
                return None
        return self._client

    async def emit(self, record: LogRecord) -> None:
        """Emit log record to Elasticsearch."""
        try:
            client = await self._get_client()
            if not client:
                return

            # Convert record to document
            doc = record.to_dict()
            if self.formatter:
                doc["formatted_message"] = self.formatter.format(record)

            # Add to buffer
            self._buffer.append({"index": {"_index": self.index, "_type": "_doc"}})
            self._buffer.append(doc)

            # Flush if buffer is full or time interval passed
            if (
                len(self._buffer) >= self._buffer_size * 2
                or (datetime.utcnow() - self._last_flush).seconds
                >= self._flush_interval
            ):
                await self.flush()

        except Exception as e:
            logging.error(f"Elasticsearch handler error: {e}")

    async def flush(self) -> None:
        """Flush buffer to Elasticsearch."""
        if not self._buffer:
            return

        try:
            client = await self._get_client()
            if not client:
                return

            # Bulk index documents
            await client.bulk(body=self._buffer)
            self._buffer.clear()
            self._last_flush = datetime.utcnow()

        except Exception as e:
            logging.error(f"Elasticsearch flush error: {e}")

    async def close(self) -> None:
        """Close Elasticsearch handler."""
        await self.flush()
        if self._client:
            await self._client.close()
            self._client = None
