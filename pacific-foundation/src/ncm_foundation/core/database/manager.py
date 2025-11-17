"""
Database manager implementation.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Type, TypeVar

from .entities import AuditLoggerImpl
from .interfaces import BaseRepository, DatabaseConfig, DatabaseProvider, DatabaseType
from .migrations import AlembicMigrationManager, MongoMigrationManager
from .pooling import ConnectionPool, PoolConfig
from .providers import DatabaseFactory, MongoDBProvider, PostgreSQLProvider
from .transactions import NestedTransactionManager, TransactionManager

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseRepository)


class DatabaseManager:
    """Unified database manager with multi-database support."""

    def __init__(
        self,
        config: DatabaseConfig,
        redis_url: Optional[str] = None,
        enable_pooling: bool = True,
        enable_audit: bool = True,
    ):
        self.config = config
        self.redis_url = redis_url
        self.enable_pooling = enable_pooling
        self.enable_audit = enable_audit

        # Initialize database provider
        self.provider = DatabaseFactory.create_provider(config)

        # Initialize connection pool if enabled
        self.connection_pool: Optional[ConnectionPool] = None
        if enable_pooling:
            pool_config = PoolConfig(
                min_connections=config.pool_size,
                max_connections=config.pool_size + config.max_overflow,
                max_overflow=config.max_overflow,
                pool_timeout=config.pool_timeout,
                pool_recycle=config.pool_recycle,
                pool_pre_ping=config.pool_pre_ping,
            )
            self.connection_pool = ConnectionPool(pool_config, self.provider)

        # Initialize transaction manager
        self.transaction_manager = TransactionManager(self.provider)
        self.nested_transaction_manager = NestedTransactionManager(self.provider)

        # Initialize migration manager
        if config.db_type == DatabaseType.POSTGRESQL:
            self.migration_manager = AlembicMigrationManager(self.provider)
        elif config.db_type == DatabaseType.MONGODB:
            self.migration_manager = MongoMigrationManager(self.provider)
        else:
            self.migration_manager = None

        # Initialize audit logger
        self.audit_logger = AuditLoggerImpl() if enable_audit else None

        # Repository registry
        self._repositories: Dict[str, BaseRepository] = {}

        self._running = False

    async def start(self) -> None:
        """Start database manager."""
        if self._running:
            logger.warning("Database manager is already running")
            return

        try:
            # Connect to database
            await self.provider.connect()

            # Initialize connection pool
            if self.connection_pool:
                await self.connection_pool.initialize()

            self._running = True
            logger.info("Database manager started")

        except Exception as e:
            logger.error(f"Failed to start database manager: {e}")
            raise

    # Backwards-compatible aliases
    async def connect(self) -> None:
        """Compatibility wrapper for older APIs expecting `connect()`.

        Delegates to `start()` which performs provider.connect() and pool
        initialization.
        """
        await self.start()

    async def stop(self) -> None:
        """Stop database manager."""
        if not self._running:
            return

        try:
            # Close connection pool
            if self.connection_pool:
                await self.connection_pool.close()

            # Disconnect from database
            await self.provider.disconnect()

            self._running = False
            logger.info("Database manager stopped")

        except Exception as e:
            logger.error(f"Failed to stop database manager: {e}")
            raise

    async def disconnect(self) -> None:
        """Compatibility wrapper for older APIs expecting `disconnect()`.

        Delegates to `stop()` which closes the pool and disconnects provider.
        """
        await self.stop()

    async def health_check(self) -> bool:
        """Check database health."""
        try:
            # Check provider health
            provider_health = await self.provider.health_check()

            # Check pool health if enabled
            pool_health = True
            if self.connection_pool:
                pool_health = await self.connection_pool.health_check()

            return provider_health and pool_health

        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    async def get_connection(self) -> Any:
        """Get database connection."""
        if self.connection_pool:
            return await self.connection_pool.get_connection()
        else:
            return await self.provider.get_connection()

    async def return_connection(self, connection: Any) -> None:
        """Return database connection."""
        if self.connection_pool:
            await self.connection_pool.return_connection(connection)
        else:
            await self.provider.return_connection(connection)

    async def get_session(self):
        """Get database session."""
        if hasattr(self.provider, "get_session"):
            # Auto-connect if not connected (for testing)
            if not self.provider._connected:
                await self.provider.connect()
            return await self.provider.get_session()
        else:
            raise AttributeError(
                f"Provider {type(self.provider).__name__} does not support sessions"
            )

    @asynccontextmanager
    async def get_session_context(self):
        """Get database session context manager."""
        if hasattr(self.provider, "get_session_context"):
            # Auto-connect if not connected (for testing)
            if not self.provider._connected:
                await self.provider.connect()
            async with self.provider.get_session_context() as session:
                yield session
        else:
            # Fallback to manual session management
            session = await self.get_session()
            try:
                yield session
            finally:
                await self.return_session(session)

    async def return_session(self, session):
        """Return database session."""
        if hasattr(self.provider, "return_session"):
            await self.provider.return_session(session)
        else:
            await session.close()

    @asynccontextmanager
    async def get_connection_context(self):
        """Get connection context manager."""
        if self.connection_pool:
            async with self.connection_pool.get_connection_context() as connection:
                yield connection
        else:
            connection = await self.get_connection()
            try:
                yield connection
            finally:
                await self.return_connection(connection)

    async def execute_query(self, query: str, params: Optional[Dict] = None) -> Any:
        """Execute a query."""
        return await self.provider.execute_query(query, params)

    async def execute_transaction(self, operations: List[Dict]) -> Any:
        """Execute multiple operations in a transaction."""
        return await self.provider.execute_transaction(operations)

    def get_transaction_manager(self) -> TransactionManager:
        """Get transaction manager."""
        return self.transaction_manager

    def get_nested_transaction_manager(self) -> NestedTransactionManager:
        """Get nested transaction manager."""
        return self.nested_transaction_manager

    def register_repository(self, name: str, repository: BaseRepository) -> None:
        """Register a repository."""
        self._repositories[name] = repository
        logger.debug(f"Registered repository: {name}")

    def get_repository(self, name: str) -> Optional[BaseRepository]:
        """Get registered repository."""
        return self._repositories.get(name)

    def get_all_repositories(self) -> Dict[str, BaseRepository]:
        """Get all registered repositories."""
        return self._repositories.copy()

    async def run_migrations(self, target_version: Optional[str] = None) -> List[Any]:
        """Run database migrations."""
        if not self.migration_manager:
            logger.warning("Migration manager not available")
            return []

        try:
            return await self.migration_manager.run_migrations(target_version)
        except Exception as e:
            logger.error(f"Failed to run migrations: {e}")
            raise

    async def rollback_migration(self, version: str) -> bool:
        """Rollback a specific migration."""
        if not self.migration_manager:
            logger.warning("Migration manager not available")
            return False

        try:
            return await self.migration_manager.rollback_migration(version)
        except Exception as e:
            logger.error(f"Failed to rollback migration {version}: {e}")
            return False

    async def get_migration_status(self) -> List[Any]:
        """Get migration status."""
        if not self.migration_manager:
            return []

        try:
            return await self.migration_manager.get_migration_status()
        except Exception as e:
            logger.error(f"Failed to get migration status: {e}")
            return []

    async def create_migration(self, name: str, description: str) -> str:
        """Create a new migration."""
        if not self.migration_manager:
            raise RuntimeError("Migration manager not available")

        try:
            return await self.migration_manager.create_migration(name, description)
        except Exception as e:
            logger.error(f"Failed to create migration: {e}")
            raise

    def get_audit_logger(self) -> Optional[AuditLoggerImpl]:
        """Get audit logger."""
        return self.audit_logger

    def get_stats(self) -> Dict[str, Any]:
        """Get database manager statistics."""
        stats = {
            "running": self._running,
            "database_type": self.config.db_type.value,
            "pooling_enabled": self.enable_pooling,
            "audit_enabled": self.enable_audit,
            "repositories_count": len(self._repositories),
        }

        # Add pool stats if available
        if self.connection_pool:
            stats["pool"] = self.connection_pool.get_stats()

        # Add provider stats
        if hasattr(self.provider, "get_stats"):
            stats["provider"] = self.provider.get_stats()

        return stats

    def get_config(self) -> Dict[str, Any]:
        """Get database configuration."""
        return {
            "db_type": self.config.db_type.value,
            "host": self.config.host,
            "port": self.config.port,
            "database": self.config.database,
            "username": self.config.username,
            "pool_size": self.config.pool_size,
            "max_overflow": self.config.max_overflow,
            "pool_timeout": self.config.pool_timeout,
            "pool_recycle": self.config.pool_recycle,
            "pool_pre_ping": self.config.pool_pre_ping,
            "echo": self.config.echo,
            "enable_pooling": self.enable_pooling,
            "enable_audit": self.enable_audit,
        }
