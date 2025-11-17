"""
SQLAlchemy connection pool implementation.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import QueuePool, StaticPool

from .base import AbstractConnectionPool, PoolStats

logger = logging.getLogger(__name__)


class SQLAlchemyConnectionPool(AbstractConnectionPool):
    """SQLAlchemy connection pool with monitoring."""

    def __init__(self, engine, pool_config: Dict[str, Any]):
        super().__init__(pool_config)
        self.engine = engine
        self._pool = None
        self._setup_pool_events()

    async def initialize(self) -> None:
        """Initialize SQLAlchemy connection pool."""
        try:
            # The engine already contains the pool, so we just need to test it
            async with self.engine.begin() as conn:
                await conn.execute("SELECT 1")

            self._pool = self.engine.pool
            self._initialized = True
            logger.info("SQLAlchemy connection pool initialized")

        except Exception as e:
            logger.error(f"Failed to initialize SQLAlchemy pool: {e}")
            raise

    async def close(self) -> None:
        """Close SQLAlchemy connection pool."""
        if self._pool and not self._closed:
            await self.engine.dispose()
            self._closed = True
            logger.info("SQLAlchemy connection pool closed")

    async def get_connection(self) -> AsyncSession:
        """Get connection from pool."""
        if not self._initialized:
            raise RuntimeError("Connection pool not initialized")

        if self._closed:
            raise RuntimeError("Connection pool is closed")

        try:
            # Create new session
            session = AsyncSession(self.engine)
            self._increment_checkouts()
            return session

        except Exception as e:
            self._increment_errors()
            logger.error(f"Failed to get connection from pool: {e}")
            raise

    async def return_connection(self, connection: AsyncSession) -> None:
        """Return connection to pool."""
        try:
            await connection.close()
            self._increment_checkins()

        except Exception as e:
            self._increment_errors()
            logger.error(f"Failed to return connection to pool: {e}")

    async def health_check(self) -> bool:
        """Check pool health."""
        try:
            async with self.engine.begin() as conn:
                await conn.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Pool health check failed: {e}")
            return False

    def get_stats(self) -> PoolStats:
        """Get pool statistics."""
        if self._pool:
            self._stats.total_connections = self._pool.size()
            self._stats.idle_connections = self._pool.checkedin()
            self._stats.overflow_connections = self._pool.overflow()

        return self._stats

    def _setup_pool_events(self) -> None:
        """Setup pool monitoring events."""

        @event.listens_for(self.engine.sync_engine, "connect")
        def on_connect(dbapi_connection, connection_record):
            """Monitor new connections."""
            self._stats.total_connections += 1
            logger.debug("New connection created")

        @event.listens_for(self.engine.sync_engine, "checkout")
        def on_checkout(dbapi_connection, connection_record, connection_proxy):
            """Monitor connection checkout."""
            self._increment_checkouts()
            logger.debug("Connection checked out from pool")

        @event.listens_for(self.engine.sync_engine, "checkin")
        def on_checkin(dbapi_connection, connection_record):
            """Monitor connection checkin."""
            self._increment_checkins()
            logger.debug("Connection checked in to pool")

        @event.listens_for(self.engine.sync_engine, "invalidate")
        def on_invalidate(dbapi_connection, connection_record, exception):
            """Monitor connection invalidation."""
            self._increment_invalidated()
            logger.warning(f"Connection invalidated: {exception}")

        @event.listens_for(self.engine.sync_engine, "close")
        def on_close(dbapi_connection, connection_record):
            """Monitor connection close."""
            logger.debug("Connection closed")

    async def get_detailed_stats(self) -> Dict[str, Any]:
        """Get detailed pool statistics."""
        stats = self.get_stats().to_dict()

        if self._pool:
            stats.update(
                {
                    "pool_size": self._pool.size(),
                    "checked_in": self._pool.checkedin(),
                    "checked_out": self._pool.checkedout(),
                    "overflow": self._pool.overflow(),
                    "invalid": self._pool.invalid(),
                    "pool_class": self._pool.__class__.__name__,
                }
            )

        return stats
