"""
Abstract database provider interface.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel

from ..config import DatabaseType


class DatabaseConfig(BaseModel):
    """Database configuration schema."""

    db_type: DatabaseType
    host: str
    port: int
    database: str
    username: str
    password: str
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600
    pool_pre_ping: bool = True
    echo: bool = False
    security_enabled: bool = False
    encryption_key: Optional[str] = None


class AbstractDatabaseProvider(ABC):
    """Abstract database provider interface."""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._connected = False

    @abstractmethod
    async def connect(self) -> None:
        """Connect to database."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from database."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check database health."""
        pass

    @abstractmethod
    async def get_session(self) -> Any:
        """Get database session."""
        pass

    @abstractmethod
    async def return_session(self, session: Any) -> None:
        """Return session to pool."""
        pass

    @abstractmethod
    async def execute_query(self, query: str, params: Optional[Dict] = None) -> Any:
        """Execute raw query."""
        pass

    @abstractmethod
    async def begin_transaction(self) -> Any:
        """Begin database transaction."""
        pass

    @abstractmethod
    async def commit_transaction(self, transaction: Any) -> None:
        """Commit transaction."""
        pass

    @abstractmethod
    async def rollback_transaction(self, transaction: Any) -> None:
        """Rollback transaction."""
        pass

    @property
    def is_connected(self) -> bool:
        """Check if provider is connected."""
        return self._connected

    async def get_stats(self) -> Dict[str, Any]:
        """Get database provider statistics."""
        return {
            "connected": self._connected,
            "db_type": self.config.db_type.value,
            "host": self.config.host,
            "port": self.config.port,
            "database": self.config.database,
        }
