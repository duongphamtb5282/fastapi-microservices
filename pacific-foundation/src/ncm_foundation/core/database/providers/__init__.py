"""
Database providers module.
"""

import importlib

from .base import AbstractDatabaseProvider, DatabaseConfig, DatabaseType
from .mongodb_provider import MongoDBProvider
from .sqlalchemy_provider import SQLAlchemyProvider

# Provide backward-compatible names expected by other modules
PostgreSQLProvider = SQLAlchemyProvider


class DatabaseFactory:
    """Database factory for creating provider instances.

    This is a thin compatibility layer so modules can import
    `DatabaseFactory` from the `providers` package.
    """

    @staticmethod
    def create_provider(config: DatabaseConfig) -> AbstractDatabaseProvider:
        if config.db_type == DatabaseType.POSTGRESQL:
            return PostgreSQLProvider(config)
        elif config.db_type == DatabaseType.MONGODB:
            return MongoDBProvider(config)
        else:
            raise ValueError(f"Unsupported database type: {config.db_type}")


class DatabaseTransaction:
    """Database transaction implementation compatible with provider API."""

    def __init__(self, provider: AbstractDatabaseProvider):
        self.provider = provider
        self._connection = None
        self._transaction = None

    async def __aenter__(self):
        """Enter transaction context."""
        # Check if provider has get_connection (for connection-based providers)
        if hasattr(self.provider, 'get_connection'):
            self._connection = await self.provider.get_connection()
            if hasattr(self._connection, "transaction"):
                self._transaction = await self._connection.transaction()
        else:
            # For session-based providers like SQLAlchemy, we don't need connection management
            pass
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit transaction context."""
        if exc_type:
            await self.rollback()
        else:
            await self.commit()

        if self._connection and hasattr(self.provider, 'return_connection'):
            await self.provider.return_connection(self._connection)

    async def commit(self) -> None:
        """Commit the transaction."""
        if self._transaction:
            await self._transaction.commit()

    async def rollback(self) -> None:
        """Rollback the transaction."""
        if self._transaction:
            await self._transaction.rollback()

    async def savepoint(self, name: str):
        """Create a savepoint if supported by the underlying connection."""
        if hasattr(self._connection, "savepoint"):
            sp = await self._connection.savepoint(name)
            return DatabaseSavepoint(sp)
        else:
            raise NotImplementedError(
                "Savepoints not supported by this database provider"
            )


class DatabaseSavepoint:
    """Simple savepoint wrapper."""

    def __init__(self, savepoint):
        self.savepoint = savepoint

    async def commit(self) -> None:
        await self.savepoint.commit()

    async def rollback(self) -> None:
        await self.savepoint.rollback()


try:
    _providers_mod = importlib.import_module("ncm_foundation.core.database.providers")
    DatabaseTransaction = getattr(_providers_mod, "DatabaseTransaction")
    DatabaseSavepoint = getattr(_providers_mod, "DatabaseSavepoint")
except Exception:
    # Providers module may not be importable at package import time in some
    # environments; fall back to defining placeholders to avoid import errors
    DatabaseTransaction = None
    DatabaseSavepoint = None

__all__ = [
    "AbstractDatabaseProvider",
    "DatabaseConfig",
    "DatabaseType",
    "SQLAlchemyProvider",
    "MongoDBProvider",
    "PostgreSQLProvider",
    "DatabaseFactory",
    "DatabaseTransaction",
    "DatabaseSavepoint",
]
