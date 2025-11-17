"""
Database provider implementations.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

import aiomysql
import aiosqlite
import asyncpg
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from .interfaces import (
    DatabaseConfig,
    DatabaseProvider,
    DatabaseType,
    Savepoint,
    Transaction,
)

logger = logging.getLogger(__name__)


class PostgreSQLProvider(DatabaseProvider):
    """PostgreSQL database provider."""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._engine = None
        self._session_factory = None
        self._connection_pool = None

    async def connect(self) -> None:
        """Connect to PostgreSQL database."""
        try:
            # Create async engine
            database_url = (
                f"postgresql+asyncpg://{self.config.username}:{self.config.password}"
                f"@{self.config.host}:{self.config.port}/{self.config.database}"
            )

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
            self._session_factory = sessionmaker(
                bind=self._engine, class_=AsyncSession, expire_on_commit=False
            )

            # Create connection pool
            self._connection_pool = await asyncpg.create_pool(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.username,
                password=self.config.password,
                min_size=self.config.pool_size,
                max_size=self.config.pool_size + self.config.max_overflow,
            )

            logger.info("Connected to PostgreSQL database")

        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from PostgreSQL database."""
        if self._connection_pool:
            await self._connection_pool.close()

        if self._engine:
            await self._engine.dispose()

        logger.info("Disconnected from PostgreSQL database")

    async def health_check(self) -> bool:
        """Check PostgreSQL health."""
        try:
            async with self._connection_pool.acquire() as conn:
                await conn.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {e}")
            return False

    async def execute_query(self, query: str, params: Optional[Dict] = None) -> Any:
        """Execute a query."""
        async with self._connection_pool.acquire() as conn:
            if params:
                return await conn.fetch(query, *params.values())
            else:
                return await conn.fetch(query)

    async def execute_transaction(self, operations: List[Dict]) -> Any:
        """Execute multiple operations in a transaction."""
        async with self._connection_pool.acquire() as conn:
            async with conn.transaction():
                results = []
                for operation in operations:
                    query = operation["query"]
                    params = operation.get("params", {})
                    result = await conn.fetch(query, *params.values())
                    results.append(result)
                return results

    async def get_connection(self) -> Any:
        """Get a database connection."""
        return await self._connection_pool.acquire()

    async def return_connection(self, connection: Any) -> None:
        """Return a database connection to the pool."""
        await connection.close()

    @asynccontextmanager
    async def get_session(self):
        """Get database session context manager."""
        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()


class MongoDBProvider(DatabaseProvider):
    """MongoDB database provider."""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._client: Optional[AsyncIOMotorClient] = None
        self._database = None

    async def connect(self) -> None:
        """Connect to MongoDB database."""
        try:
            # Create MongoDB connection string
            connection_string = (
                f"mongodb://{self.config.username}:{self.config.password}"
                f"@{self.config.host}:{self.config.port}/{self.config.database}"
            )

            self._client = AsyncIOMotorClient(connection_string)
            self._database = self._client[self.config.database]

            # Test connection
            await self._client.admin.command("ping")

            logger.info("Connected to MongoDB database")

        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from MongoDB database."""
        if self._client:
            self._client.close()

        logger.info("Disconnected from MongoDB database")

    async def health_check(self) -> bool:
        """Check MongoDB health."""
        try:
            await self._client.admin.command("ping")
            return True
        except Exception as e:
            logger.error(f"MongoDB health check failed: {e}")
            return False

    async def execute_query(self, query: str, params: Optional[Dict] = None) -> Any:
        """Execute a query."""
        # MongoDB queries are handled differently
        # This is a placeholder for MongoDB-specific query execution
        collection_name = params.get("collection") if params else "default"
        collection = self._database[collection_name]

        # Execute MongoDB operation based on query type
        if query.startswith("find"):
            return await collection.find(params.get("filter", {})).to_list(length=None)
        elif query.startswith("insert"):
            return await collection.insert_one(params.get("document", {}))
        elif query.startswith("update"):
            return await collection.update_many(
                params.get("filter", {}), params.get("update", {})
            )
        elif query.startswith("delete"):
            return await collection.delete_many(params.get("filter", {}))
        else:
            raise ValueError(f"Unsupported MongoDB query: {query}")

    async def execute_transaction(self, operations: List[Dict]) -> Any:
        """Execute multiple operations in a transaction."""
        async with await self._client.start_session() as session:
            async with session.start_transaction():
                results = []
                for operation in operations:
                    result = await self.execute_query(
                        operation["query"], operation.get("params", {})
                    )
                    results.append(result)
                return results

    async def get_connection(self) -> Any:
        """Get a database connection."""
        return self._database

    async def return_connection(self, connection: Any) -> None:
        """Return a database connection to the pool."""
        # MongoDB connections are handled automatically
        pass


class DatabaseFactory:
    """Database factory for creating providers."""

    @staticmethod
    def create_provider(config: DatabaseConfig) -> DatabaseProvider:
        """Create database provider based on configuration."""
        if config.db_type == DatabaseType.POSTGRESQL:
            return PostgreSQLProvider(config)
        elif config.db_type == DatabaseType.MONGODB:
            return MongoDBProvider(config)
        else:
            raise ValueError(f"Unsupported database type: {config.db_type}")


class DatabaseTransaction(Transaction):
    """Database transaction implementation."""

    def __init__(self, provider: DatabaseProvider):
        self.provider = provider
        self._connection = None
        self._transaction = None

    async def __aenter__(self):
        """Enter transaction context."""
        self._connection = await self.provider.get_connection()
        if hasattr(self._connection, "transaction"):
            self._transaction = await self._connection.transaction()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit transaction context."""
        if exc_type:
            await self.rollback()
        else:
            await self.commit()

        if self._connection:
            await self.provider.return_connection(self._connection)

    async def commit(self) -> None:
        """Commit the transaction."""
        if self._transaction:
            await self._transaction.commit()

    async def rollback(self) -> None:
        """Rollback the transaction."""
        if self._transaction:
            await self._transaction.rollback()

    async def savepoint(self, name: str) -> "DatabaseSavepoint":
        """Create a savepoint."""
        if hasattr(self._connection, "savepoint"):
            sp = await self._connection.savepoint(name)
            return DatabaseSavepoint(sp)
        else:
            raise NotImplementedError(
                "Savepoints not supported by this database provider"
            )


class DatabaseSavepoint(Savepoint):
    """Database savepoint implementation."""

    def __init__(self, savepoint):
        self.savepoint = savepoint

    async def commit(self) -> None:
        """Commit the savepoint."""
        await self.savepoint.commit()

    async def rollback(self) -> None:
        """Rollback the savepoint."""
        await self.savepoint.rollback()
