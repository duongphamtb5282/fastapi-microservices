"""
Abstract connection pool interface.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class PoolStats:
    """Connection pool statistics."""

    def __init__(self):
        self.total_connections: int = 0
        self.active_connections: int = 0
        self.idle_connections: int = 0
        self.overflow_connections: int = 0
        self.checkouts: int = 0
        self.checkins: int = 0
        self.invalidated: int = 0
        self.errors: int = 0
        self.created_at: datetime = datetime.utcnow()
        self.last_activity: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            "total_connections": self.total_connections,
            "active_connections": self.active_connections,
            "idle_connections": self.idle_connections,
            "overflow_connections": self.overflow_connections,
            "checkouts": self.checkouts,
            "checkins": self.checkins,
            "invalidated": self.invalidated,
            "errors": self.errors,
            "created_at": self.created_at.isoformat(),
            "last_activity": (
                self.last_activity.isoformat() if self.last_activity else None
            ),
        }


class AbstractConnectionPool(ABC):
    """Abstract connection pool interface."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._stats = PoolStats()
        self._initialized = False
        self._closed = False

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize connection pool."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close connection pool."""
        pass

    @abstractmethod
    async def get_connection(self) -> Any:
        """Get connection from pool."""
        pass

    @abstractmethod
    async def return_connection(self, connection: Any) -> None:
        """Return connection to pool."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check pool health."""
        pass

    @abstractmethod
    def get_stats(self) -> PoolStats:
        """Get pool statistics."""
        pass

    @asynccontextmanager
    async def get_connection_context(self):
        """Get connection context manager."""
        connection = await self.get_connection()
        try:
            yield connection
        finally:
            await self.return_connection(connection)

    @property
    def is_initialized(self) -> bool:
        """Check if pool is initialized."""
        return self._initialized

    @property
    def is_closed(self) -> bool:
        """Check if pool is closed."""
        return self._closed

    def _update_activity(self) -> None:
        """Update last activity timestamp."""
        self._stats.last_activity = datetime.utcnow()

    def _increment_checkouts(self) -> None:
        """Increment checkout counter."""
        self._stats.checkouts += 1
        self._stats.active_connections += 1
        self._update_activity()

    def _increment_checkins(self) -> None:
        """Increment checkin counter."""
        self._stats.checkins += 1
        self._stats.active_connections -= 1
        self._update_activity()

    def _increment_errors(self) -> None:
        """Increment error counter."""
        self._stats.errors += 1
        self._update_activity()

    def _increment_invalidated(self) -> None:
        """Increment invalidated counter."""
        self._stats.invalidated += 1
        self._update_activity()
