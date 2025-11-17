"""
Database session management.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .models.listeners import audit_context, setup_all_listeners
from .providers.base import AbstractDatabaseProvider

logger = logging.getLogger(__name__)


class DatabaseSessionManager:
    """Database session manager with connection pooling."""

    def __init__(self, provider: AbstractDatabaseProvider):
        self.provider = provider
        self._session_factory: Optional[async_sessionmaker] = None
        self._setup_session_factory()

    def _setup_session_factory(self) -> None:
        """Setup session factory based on provider type."""
        if hasattr(self.provider, "_session_factory"):
            self._session_factory = self.provider._session_factory
        else:
            # For MongoDB, we don't need a session factory
            self._session_factory = None

    @asynccontextmanager
    async def get_session(self):
        """Get database session context manager."""
        if self._session_factory:
            # SQLAlchemy session
            async with self._session_factory() as session:
                try:
                    yield session
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise
                finally:
                    await session.close()
        else:
            # MongoDB session
            session = await self.provider.get_session()
            try:
                yield session
            finally:
                await self.provider.return_session(session)

    async def get_session_sync(self) -> Any:
        """Get synchronous session (for compatibility)."""
        if self._session_factory:
            return await self._session_factory()
        else:
            return await self.provider.get_session()

    async def close_session(self, session: Any) -> None:
        """Close database session."""
        if hasattr(session, "close"):
            await session.close()
        else:
            await self.provider.return_session(session)

    def set_audit_user(self, user_id: str) -> None:
        """Set current user for audit logging."""
        audit_context.set_user(user_id)

    def clear_audit_user(self) -> None:
        """Clear current user from audit context."""
        audit_context.clear()


class DatabaseManager:
    """Unified database manager."""

    def __init__(self, provider: AbstractDatabaseProvider):
        self.provider = provider
        self.session_manager = DatabaseSessionManager(provider)
        self._connected = False

    async def connect(self) -> None:
        """Connect to database."""
        try:
            await self.provider.connect()
            self._connected = True

            # Setup database listeners
            setup_all_listeners()

            logger.info("Database manager connected")
        except Exception as e:
            logger.error(f"Failed to connect database manager: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from database."""
        try:
            await self.provider.disconnect()
            self._connected = False
            logger.info("Database manager disconnected")
        except Exception as e:
            logger.error(f"Failed to disconnect database manager: {e}")
            raise

    async def health_check(self) -> bool:
        """Check database health."""
        try:
            return await self.provider.health_check()
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    @asynccontextmanager
    async def get_session(self):
        """Get database session."""
        if not self._connected:
            raise RuntimeError("Database manager not connected")

        async with self.session_manager.get_session() as session:
            yield session

    async def execute_query(self, query: str, params: Optional[Dict] = None) -> Any:
        """Execute raw query."""
        return await self.provider.execute_query(query, params)

    async def begin_transaction(self) -> Any:
        """Begin database transaction."""
        return await self.provider.begin_transaction()

    async def commit_transaction(self, transaction: Any) -> None:
        """Commit database transaction."""
        await self.provider.commit_transaction(transaction)

    async def rollback_transaction(self, transaction: Any) -> None:
        """Rollback database transaction."""
        await self.provider.rollback_transaction(transaction)

    def get_session_manager(self) -> DatabaseSessionManager:
        """Get session manager."""
        return self.session_manager

    def get_provider(self) -> AbstractDatabaseProvider:
        """Get database provider."""
        return self.provider

    async def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        stats = {
            "connected": self._connected,
            "provider_type": self.provider.__class__.__name__,
        }

        # Get provider-specific stats
        if hasattr(self.provider, "get_stats"):
            provider_stats = await self.provider.get_stats()
            stats.update(provider_stats)

        return stats


# Global database manager instance
_database_manager: Optional[DatabaseManager] = None


async def get_database_manager() -> DatabaseManager:
    """Get global database manager instance."""
    global _database_manager
    if _database_manager is None:
        raise RuntimeError("Database manager not initialized")
    return _database_manager


async def initialize_database_manager(
    provider: AbstractDatabaseProvider,
) -> DatabaseManager:
    """Initialize global database manager."""
    global _database_manager
    _database_manager = DatabaseManager(provider)
    await _database_manager.connect()
    return _database_manager


async def close_database_manager() -> None:
    """Close global database manager."""
    global _database_manager
    if _database_manager:
        await _database_manager.disconnect()
        _database_manager = None
