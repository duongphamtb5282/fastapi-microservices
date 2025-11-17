"""
Database engine configuration and factory.
"""

import logging
from typing import Any, Dict, Optional

from motor.motor_asyncio import AsyncIOMotorClient
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import QueuePool, StaticPool

from .config import DatabaseConfig, DatabaseType
from .providers.mongodb_provider import MongoDBProvider
from .providers.sqlalchemy_provider import SQLAlchemyProvider

logger = logging.getLogger(__name__)


class DatabaseEngineFactory:
    """Factory for creating database engines and providers."""

    @staticmethod
    def create_provider(config: DatabaseConfig) -> Any:
        """Create database provider based on configuration."""
        if config.db_type == DatabaseType.POSTGRESQL:
            return SQLAlchemyProvider(config)
        elif config.db_type == DatabaseType.MYSQL:
            return SQLAlchemyProvider(config)
        elif config.db_type == DatabaseType.SQLITE:
            return SQLAlchemyProvider(config)
        elif config.db_type == DatabaseType.MONGODB:
            return MongoDBProvider(config)
        else:
            raise ValueError(f"Unsupported database type: {config.db_type}")

    @staticmethod
    def create_sqlalchemy_engine(config: DatabaseConfig) -> AsyncEngine:
        """Create SQLAlchemy async engine."""
        database_url = DatabaseEngineFactory._build_database_url(config)

        # Choose pool class based on database type
        pool_class = QueuePool
        if config.db_type == DatabaseType.SQLITE:
            pool_class = StaticPool

        engine = create_async_engine(
            database_url,
            poolclass=pool_class,
            pool_size=config.pool_size,
            max_overflow=config.max_overflow,
            pool_timeout=config.pool_timeout,
            pool_recycle=config.pool_recycle,
            pool_pre_ping=config.pool_pre_ping,
            echo=config.echo,
            future=True,
        )

        logger.info(f"Created SQLAlchemy engine for {config.db_type.value}")
        return engine

    @staticmethod
    def create_mongodb_client(config: DatabaseConfig) -> AsyncIOMotorClient:
        """Create MongoDB async client."""
        connection_string = DatabaseEngineFactory._build_mongodb_connection_string(
            config
        )

        client = AsyncIOMotorClient(
            connection_string,
            maxPoolSize=config.pool_size + config.max_overflow,
            minPoolSize=config.pool_size,
            maxIdleTimeMS=config.pool_recycle * 1000,
            serverSelectionTimeoutMS=config.pool_timeout * 1000,
            connectTimeoutMS=config.pool_timeout * 1000,
            socketTimeoutMS=config.pool_timeout * 1000,
            retryWrites=True,
            retryReads=True,
        )

        logger.info(f"Created MongoDB client for {config.database}")
        return client

    @staticmethod
    def _build_database_url(config: DatabaseConfig) -> str:
        """Build database URL based on configuration."""
        if config.db_type == DatabaseType.POSTGRESQL:
            return (
                f"postgresql+asyncpg://{config.username}:{config.password}"
                f"@{config.host}:{config.port}/{config.database}"
            )
        elif config.db_type == DatabaseType.MYSQL:
            return (
                f"mysql+aiomysql://{config.username}:{config.password}"
                f"@{config.host}:{config.port}/{config.database}"
            )
        elif config.db_type == DatabaseType.SQLITE:
            return f"sqlite+aiosqlite:///{config.database}"
        else:
            raise ValueError(
                f"Unsupported database type for SQLAlchemy: {config.db_type}"
            )

    @staticmethod
    def _build_mongodb_connection_string(config: DatabaseConfig) -> str:
        """Build MongoDB connection string."""
        if config.username and config.password:
            return (
                f"mongodb://{config.username}:{config.password}"
                f"@{config.host}:{config.port}/{config.database}"
            )
        else:
            return f"mongodb://{config.host}:{config.port}/{config.database}"


class DatabaseEngineManager:
    """Database engine manager with lifecycle management."""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.engine: Optional[AsyncEngine] = None
        self.mongodb_client: Optional[AsyncIOMotorClient] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize database engine."""
        try:
            if self.config.db_type in [
                DatabaseType.POSTGRESQL,
                DatabaseType.MYSQL,
                DatabaseType.SQLITE,
            ]:
                self.engine = DatabaseEngineFactory.create_sqlalchemy_engine(
                    self.config
                )
                logger.info(
                    f"SQLAlchemy engine initialized for {self.config.db_type.value}"
                )
            elif self.config.db_type == DatabaseType.MONGODB:
                self.mongodb_client = DatabaseEngineFactory.create_mongodb_client(
                    self.config
                )
                logger.info(f"MongoDB client initialized for {self.config.database}")

            self._initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize database engine: {e}")
            raise

    async def close(self) -> None:
        """Close database engine."""
        try:
            if self.engine:
                await self.engine.dispose()
                self.engine = None
                logger.info("SQLAlchemy engine disposed")

            if self.mongodb_client:
                self.mongodb_client.close()
                self.mongodb_client = None
                logger.info("MongoDB client closed")

            self._initialized = False
        except Exception as e:
            logger.error(f"Failed to close database engine: {e}")
            raise

    async def health_check(self) -> bool:
        """Check engine health."""
        try:
            if self.engine:
                async with self.engine.begin() as conn:
                    await conn.execute("SELECT 1")
                return True
            elif self.mongodb_client:
                await self.mongodb_client.admin.command("ping")
                return True
            return False
        except Exception as e:
            logger.error(f"Database engine health check failed: {e}")
            return False

    def get_engine(self) -> Optional[AsyncEngine]:
        """Get SQLAlchemy engine."""
        return self.engine

    def get_mongodb_client(self) -> Optional[AsyncIOMotorClient]:
        """Get MongoDB client."""
        return self.mongodb_client

    def get_database(self) -> Optional[Any]:
        """Get database instance."""
        if self.mongodb_client:
            return self.mongodb_client[self.config.database]
        return None

    async def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        stats = {
            "initialized": self._initialized,
            "db_type": self.config.db_type.value,
            "host": self.config.host,
            "port": self.config.port,
            "database": self.config.database,
        }

        if self.engine:
            pool = self.engine.pool
            stats.update(
                {
                    "pool_size": pool.size(),
                    "checked_in": pool.checkedin(),
                    "checked_out": pool.checkedout(),
                    "overflow": pool.overflow(),
                    "invalid": pool.invalid(),
                }
            )

        return stats


# Global engine manager instance
_engine_manager: Optional[DatabaseEngineManager] = None


async def get_engine_manager() -> DatabaseEngineManager:
    """Get global engine manager instance."""
    global _engine_manager
    if _engine_manager is None:
        raise RuntimeError("Engine manager not initialized")
    return _engine_manager


async def initialize_engine_manager(config: DatabaseConfig) -> DatabaseEngineManager:
    """Initialize global engine manager."""
    global _engine_manager
    _engine_manager = DatabaseEngineManager(config)
    await _engine_manager.initialize()
    return _engine_manager


async def close_engine_manager() -> None:
    """Close global engine manager."""
    global _engine_manager
    if _engine_manager:
        await _engine_manager.close()
        _engine_manager = None
