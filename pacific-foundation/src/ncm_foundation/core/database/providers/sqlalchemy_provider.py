"""
SQLAlchemy database provider with connection pooling.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from ..config import DatabaseType
from .base import AbstractDatabaseProvider, DatabaseConfig

logger = logging.getLogger(__name__)


class SQLAlchemyProvider(AbstractDatabaseProvider):
    """SQLAlchemy database provider with connection pooling."""

    def __init__(self, config: DatabaseConfig):
        super().__init__(config)
        self._engine = None
        self._session_factory = None
        self._pool = None
        self._pool_stats = {
            "total_connections": 0,
            "active_connections": 0,
            "idle_connections": 0,
            "overflow_connections": 0,
            "checkouts": 0,
            "checkins": 0,
            "invalidated": 0,
        }

    async def connect(self) -> None:
        """Connect to database with connection pooling."""
        try:
            # Create async engine with connection pooling
            database_url = self._build_database_url()

            self._engine = create_async_engine(
                database_url,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
                pool_timeout=self.config.pool_timeout,
                pool_recycle=self.config.pool_recycle,
                pool_pre_ping=self.config.pool_pre_ping,
                echo=self.config.echo,
            )

            # Create session factory
            self._session_factory = async_sessionmaker(
                bind=self._engine, class_=AsyncSession, expire_on_commit=False
            )

            # Setup connection pool monitoring
            self._setup_pool_monitoring()

            # Test connection
            async with self._engine.begin() as conn:
                await conn.execute(text("SELECT 1"))

            self._connected = True
            logger.info(f"Connected to {self.config.db_type.value} database")

        except Exception as e:
            logger.error(f"Failed to connect to {self.config.db_type.value}: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from database."""
        if self._engine:
            await self._engine.dispose()
            self._connected = False
            logger.info(f"Disconnected from {self.config.db_type.value} database")

    async def health_check(self) -> bool:
        """Check database health."""
        try:
            async with self._engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    async def get_session(self) -> AsyncSession:
        """Get database session."""
        if not self._connected:
            raise RuntimeError("Database provider not connected")

        return self._session_factory()

    async def return_session(self, session: AsyncSession) -> None:
        """Return session to pool."""
        await session.close()

    @asynccontextmanager
    async def get_session_context(self):
        """Get session context manager."""
        session = await self.get_session()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await self.return_session(session)

    async def execute_query(self, query: str, params: Optional[Dict] = None) -> Any:
        """Execute raw query."""
        async with self.get_session_context() as session:
            result = await session.execute(text(query), params or {})
            return result.fetchall()

    async def begin_transaction(self) -> AsyncSession:
        """Begin database transaction."""
        session = await self.get_session()
        return session

    async def commit_transaction(self, transaction: AsyncSession) -> None:
        """Commit transaction."""
        await transaction.commit()
        await self.return_session(transaction)

    async def rollback_transaction(self, transaction: AsyncSession) -> None:
        """Rollback transaction."""
        await transaction.rollback()
        await self.return_session(transaction)

    def _build_database_url(self) -> str:
        """Build database URL based on configuration."""
        if self.config.db_type == DatabaseType.POSTGRESQL:
            return (
                f"postgresql+asyncpg://{self.config.username}:{self.config.password}"
                f"@{self.config.host}:{self.config.port}/{self.config.database}"
            )
        elif self.config.db_type == DatabaseType.MYSQL:
            return (
                f"mysql+aiomysql://{self.config.username}:{self.config.password}"
                f"@{self.config.host}:{self.config.port}/{self.config.database}"
            )
        elif self.config.db_type == DatabaseType.SQLITE:
            return f"sqlite+aiosqlite:///{self.config.database}"
        else:
            raise ValueError(f"Unsupported database type: {self.config.db_type}")

    def _setup_pool_monitoring(self) -> None:
        """Setup connection pool monitoring and events."""

        @event.listens_for(self._engine.sync_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """Setup database-specific optimizations."""
            if self.config.db_type == DatabaseType.SQLITE:
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        @event.listens_for(self._engine.sync_engine, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            """Monitor connection checkout."""
            self._pool_stats["checkouts"] += 1
            self._pool_stats["active_connections"] += 1
            logger.debug("Connection checked out from pool")

        @event.listens_for(self._engine.sync_engine, "checkin")
        def receive_checkin(dbapi_connection, connection_record):
            """Monitor connection checkin."""
            self._pool_stats["checkins"] += 1
            self._pool_stats["active_connections"] -= 1
            logger.debug("Connection checked in to pool")

        @event.listens_for(self._engine.sync_engine, "invalidate")
        def receive_invalidate(dbapi_connection, connection_record, exception):
            """Monitor connection invalidation."""
            self._pool_stats["invalidated"] += 1
            logger.warning(f"Connection invalidated: {exception}")

    async def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        pool = self._engine.pool
        return {
            **self._pool_stats,
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "invalid": pool.invalid(),
        }
