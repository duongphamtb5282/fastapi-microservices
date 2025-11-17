"""
MongoDB database provider with connection pooling.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from bson import ObjectId
from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorCollection,
    AsyncIOMotorDatabase,
)
from pymongo import MongoClient

from ..config import DatabaseType
from .base import AbstractDatabaseProvider, DatabaseConfig

logger = logging.getLogger(__name__)


class MongoDBProvider(AbstractDatabaseProvider):
    """MongoDB provider with connection pooling."""

    def __init__(self, config: DatabaseConfig):
        super().__init__(config)
        self._client: Optional[AsyncIOMotorClient] = None
        self._database: Optional[AsyncIOMotorDatabase] = None
        self._pool_stats = {
            "total_connections": 0,
            "active_connections": 0,
            "idle_connections": 0,
            "operations": 0,
            "errors": 0,
        }

    async def connect(self) -> None:
        """Connect to MongoDB with connection pooling."""
        try:
            # Create MongoDB connection string
            connection_string = self._build_connection_string()

            # Create async client with connection pooling
            self._client = AsyncIOMotorClient(
                connection_string,
                maxPoolSize=self.config.pool_size + self.config.max_overflow,
                minPoolSize=self.config.pool_size,
                maxIdleTimeMS=self.config.pool_recycle * 1000,
                serverSelectionTimeoutMS=self.config.pool_timeout * 1000,
                connectTimeoutMS=self.config.pool_timeout * 1000,
                socketTimeoutMS=self.config.pool_timeout * 1000,
                retryWrites=True,
                retryReads=True,
            )

            self._database = self._client[self.config.database]

            # Test connection
            await self._client.admin.command("ping")

            self._connected = True
            logger.info(f"Connected to MongoDB database: {self.config.database}")

        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from MongoDB database."""
        if self._client:
            self._client.close()
            self._connected = False
            logger.info("Disconnected from MongoDB database")

    async def health_check(self) -> bool:
        """Check MongoDB health."""
        try:
            await self._client.admin.command("ping")
            return True
        except Exception as e:
            logger.error(f"MongoDB health check failed: {e}")
            return False

    async def get_session(self) -> AsyncIOMotorDatabase:
        """Get database session."""
        if not self._connected:
            raise RuntimeError("MongoDB provider not connected")

        return self._database

    async def return_session(self, session: AsyncIOMotorDatabase) -> None:
        """Return session to pool (MongoDB handles this automatically)."""
        pass

    @asynccontextmanager
    async def get_session_context(self):
        """Get session context manager."""
        session = await self.get_session()
        try:
            yield session
        finally:
            # MongoDB connections are handled automatically
            pass

    async def execute_query(self, query: str, params: Optional[Dict] = None) -> Any:
        """Execute MongoDB query."""
        try:
            collection_name = params.get("collection") if params else "default"
            collection = self._database[collection_name]

            # Execute MongoDB operation based on query type
            if query.startswith("find"):
                cursor = collection.find(params.get("filter", {}))
                return await cursor.to_list(length=params.get("limit", 1000))
            elif query.startswith("insert"):
                result = await collection.insert_one(params.get("document", {}))
                return {"inserted_id": result.inserted_id}
            elif query.startswith("update"):
                result = await collection.update_many(
                    params.get("filter", {}), params.get("update", {})
                )
                return {
                    "matched_count": result.matched_count,
                    "modified_count": result.modified_count,
                }
            elif query.startswith("delete"):
                result = await collection.delete_many(params.get("filter", {}))
                return {"deleted_count": result.deleted_count}
            else:
                raise ValueError(f"Unsupported MongoDB query: {query}")

        except Exception as e:
            self._pool_stats["errors"] += 1
            logger.error(f"MongoDB query execution failed: {e}")
            raise

    async def begin_transaction(self) -> Any:
        """Begin MongoDB transaction."""
        session = await self._client.start_session()
        return session

    async def commit_transaction(self, transaction: Any) -> None:
        """Commit MongoDB transaction."""
        await transaction.commit_transaction()
        await transaction.end_session()

    async def rollback_transaction(self, transaction: Any) -> None:
        """Rollback MongoDB transaction."""
        await transaction.abort_transaction()
        await transaction.end_session()

    def _build_connection_string(self) -> str:
        """Build MongoDB connection string."""
        if self.config.username and self.config.password:
            return (
                f"mongodb://{self.config.username}:{self.config.password}"
                f"@{self.config.host}:{self.config.port}/{self.config.database}"
            )
        else:
            return f"mongodb://{self.config.host}:{self.config.port}/{self.config.database}"

    async def get_collection(self, collection_name: str) -> AsyncIOMotorCollection:
        """Get MongoDB collection."""
        if not self._connected:
            raise RuntimeError("MongoDB provider not connected")

        return self._database[collection_name]

    async def create_index(
        self, collection_name: str, index_spec: Dict[str, Any]
    ) -> str:
        """Create index on collection."""
        collection = await self.get_collection(collection_name)
        return await collection.create_index(list(index_spec.items()))

    async def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        if not self._client:
            return self._pool_stats

        # Get server info
        server_info = await self._client.server_info()

        return {
            **self._pool_stats,
            "server_version": server_info.get("version"),
            "max_bson_object_size": server_info.get("maxBsonObjectSize"),
            "max_message_size_bytes": server_info.get("maxMessageSizeBytes"),
        }
