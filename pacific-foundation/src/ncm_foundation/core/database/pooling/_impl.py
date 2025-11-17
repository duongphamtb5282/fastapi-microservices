"""
Internal implementation module for connection pooling.

This file contains the PoolConfig dataclass and ConnectionPool implementation
that are exported by the `pooling` package. Keeping implementation in a
submodule avoids name collisions with other top-level modules.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PoolState(Enum):
    """Connection pool state."""

    INITIALIZING = "initializing"
    RUNNING = "running"
    DRAINING = "draining"
    CLOSED = "closed"


@dataclass
class PoolConfig:
    """Connection pool configuration."""

    min_connections: int = 5
    max_connections: int = 20
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 3600
    pool_pre_ping: bool = True
    pool_reset_on_return: str = "rollback"  # "commit", "rollback", "none"


class ConnectionPool:
    """Generic connection pool implementation."""

    def __init__(self, config: PoolConfig, provider: Any):
        self.config = config
        self.provider = provider
        self._pool: Optional[Any] = None
        self._state = PoolState.INITIALIZING
        self._connections: List[Any] = []
        self._available_connections: asyncio.Queue = asyncio.Queue()
        self._lock = asyncio.Lock()
        self._stats = {
            "total_connections": 0,
            "active_connections": 0,
            "idle_connections": 0,
            "connection_requests": 0,
            "connection_waits": 0,
            "connection_timeouts": 0,
        }

    async def initialize(self) -> None:
        """Initialize the connection pool."""
        async with self._lock:
            if self._state != PoolState.INITIALIZING:
                return

            try:
                # Create initial connections
                for _ in range(self.config.min_connections):
                    connection = await self._create_connection()
                    self._connections.append(connection)
                    await self._available_connections.put(connection)

                self._stats["total_connections"] = len(self._connections)
                self._stats["idle_connections"] = len(self._connections)
                self._state = PoolState.RUNNING

                logger.info(
                    f"Connection pool initialized with {len(self._connections)} connections"
                )

            except Exception as e:
                logger.error(f"Failed to initialize connection pool: {e}")
                await self._cleanup_connections()
                raise

    async def _create_connection(self) -> Any:
        """Create a new database connection."""
        try:
            if hasattr(self.provider, "get_connection"):
                return await self.provider.get_connection()
            else:
                # Fallback for providers without get_connection method
                return await self.provider.connect()
        except Exception as e:
            logger.error(f"Failed to create connection: {e}")
            raise

    async def get_connection(self) -> Any:
        """Get a connection from the pool."""
        self._stats["connection_requests"] += 1

        try:
            # Try to get an available connection
            try:
                connection = await asyncio.wait_for(
                    self._available_connections.get(), timeout=self.config.pool_timeout
                )
            except asyncio.TimeoutError:
                self._stats["connection_timeouts"] += 1
                raise RuntimeError("Connection pool timeout")

            # Check if connection is still valid
            if await self._is_connection_valid(connection):
                self._stats["active_connections"] += 1
                self._stats["idle_connections"] -= 1
                return connection
            else:
                # Connection is invalid, create a new one
                await self._close_connection(connection)
                return await self._get_or_create_connection()

        except Exception as e:
            logger.error(f"Failed to get connection from pool: {e}")
            raise

    async def _get_or_create_connection(self) -> Any:
        """Get existing connection or create new one if under limit."""
        async with self._lock:
            if len(self._connections) < self.config.max_connections:
                # Create new connection
                connection = await self._create_connection()
                self._connections.append(connection)
                self._stats["total_connections"] += 1
                self._stats["active_connections"] += 1
                return connection
            else:
                # Wait for available connection
                self._stats["connection_waits"] += 1
                return await self.get_connection()

    async def return_connection(self, connection: Any) -> None:
        """Return a connection to the pool."""
        try:
            # Reset connection if configured
            if self.config.pool_reset_on_return == "rollback":
                await self._rollback_connection(connection)
            elif self.config.pool_reset_on_return == "commit":
                await self._commit_connection(connection)

            # Check if connection is still valid
            if await self._is_connection_valid(connection):
                await self._available_connections.put(connection)
                self._stats["active_connections"] -= 1
                self._stats["idle_connections"] += 1
            else:
                # Connection is invalid, remove it
                await self._close_connection(connection)
                self._connections.remove(connection)
                self._stats["total_connections"] -= 1
                self._stats["active_connections"] -= 1

        except Exception as e:
            logger.error(f"Failed to return connection to pool: {e}")

    async def _is_connection_valid(self, connection: Any) -> bool:
        """Check if connection is still valid."""
        try:
            if hasattr(connection, "execute"):
                await connection.execute("SELECT 1")
                return True
            elif hasattr(connection, "ping"):
                await connection.ping()
                return True
            else:
                # Assume connection is valid if no validation method
                return True
        except Exception:
            return False

    async def _rollback_connection(self, connection: Any) -> None:
        """Rollback connection."""
        try:
            if hasattr(connection, "rollback"):
                await connection.rollback()
        except Exception as e:
            logger.warning(f"Failed to rollback connection: {e}")

    async def _commit_connection(self, connection: Any) -> None:
        """Commit connection."""
        try:
            if hasattr(connection, "commit"):
                await connection.commit()
        except Exception as e:
            logger.warning(f"Failed to commit connection: {e}")

    async def _close_connection(self, connection: Any) -> None:
        """Close a connection."""
        try:
            if hasattr(connection, "close"):
                await connection.close()
        except Exception as e:
            logger.warning(f"Failed to close connection: {e}")

    @asynccontextmanager
    async def get_connection_context(self):
        """Get connection context manager."""
        connection = None
        try:
            connection = await self.get_connection()
            yield connection
        finally:
            if connection:
                await self.return_connection(connection)

    async def health_check(self) -> bool:
        """Check pool health."""
        try:
            async with self.get_connection_context() as connection:
                return await self._is_connection_valid(connection)
        except Exception as e:
            logger.error(f"Connection pool health check failed: {e}")
            return False

    async def close(self) -> None:
        """Close the connection pool."""
        async with self._lock:
            if self._state == PoolState.CLOSED:
                return

            self._state = PoolState.DRAINING

            # Close all connections
            await self._cleanup_connections()

            self._state = PoolState.CLOSED
            logger.info("Connection pool closed")

    async def _cleanup_connections(self) -> None:
        """Clean up all connections."""
        for connection in self._connections:
            await self._close_connection(connection)

        self._connections.clear()
        self._stats["total_connections"] = 0
        self._stats["active_connections"] = 0
        self._stats["idle_connections"] = 0

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        return {
            **self._stats,
            "state": self._state.value,
            "config": {
                "min_connections": self.config.min_connections,
                "max_connections": self.config.max_connections,
                "max_overflow": self.config.max_overflow,
                "pool_timeout": self.config.pool_timeout,
                "pool_recycle": self.config.pool_recycle,
                "pool_pre_ping": self.config.pool_pre_ping,
                "pool_reset_on_return": self.config.pool_reset_on_return,
            },
        }

    def get_utilization(self) -> float:
        """Get pool utilization percentage."""
        if self._stats["total_connections"] == 0:
            return 0.0

        return (
            self._stats["active_connections"] / self._stats["total_connections"]
        ) * 100
