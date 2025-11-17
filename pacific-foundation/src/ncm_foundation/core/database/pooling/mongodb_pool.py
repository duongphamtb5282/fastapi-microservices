"""
MongoDB connection pool implementation.
"""

import asyncio
import logging
from typing import Any, Dict, Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from .base import AbstractConnectionPool, PoolStats

logger = logging.getLogger(__name__)


class MongoDBConnectionPool(AbstractConnectionPool):
    """MongoDB connection pool implementation."""

    def __init__(self, client: AsyncIOMotorClient, pool_config: Dict[str, Any]):
        super().__init__(pool_config)
        self.client = client
        self._database: Optional[AsyncIOMotorDatabase] = None

    async def initialize(self) -> None:
        """Initialize MongoDB connection pool."""
        try:
            # Test connection
            await self.client.admin.command("ping")

            # Get database
            self._database = self.client[self.config.get("database", "ncm")]

            self._initialized = True
            logger.info("MongoDB connection pool initialized")

        except Exception as e:
            logger.error(f"Failed to initialize MongoDB pool: {e}")
            raise

    async def close(self) -> None:
        """Close MongoDB connection pool."""
        if not self._closed:
            self.client.close()
            self._closed = True
            logger.info("MongoDB connection pool closed")

    async def get_connection(self) -> AsyncIOMotorDatabase:
        """Get connection from pool."""
        if not self._initialized:
            raise RuntimeError("Connection pool not initialized")

        if self._closed:
            raise RuntimeError("Connection pool is closed")

        try:
            self._increment_checkouts()
            return self._database

        except Exception as e:
            self._increment_errors()
            logger.error(f"Failed to get connection from pool: {e}")
            raise

    async def return_connection(self, connection: AsyncIOMotorDatabase) -> None:
        """Return connection to pool (MongoDB handles this automatically)."""
        try:
            self._increment_checkins()

        except Exception as e:
            self._increment_errors()
            logger.error(f"Failed to return connection to pool: {e}")

    async def health_check(self) -> bool:
        """Check pool health."""
        try:
            await self.client.admin.command("ping")
            return True
        except Exception as e:
            logger.error(f"MongoDB pool health check failed: {e}")
            return False

    def get_stats(self) -> PoolStats:
        """Get pool statistics."""
        # MongoDB doesn't expose detailed pool stats like SQLAlchemy
        # We can only track our own metrics
        return self._stats

    async def get_detailed_stats(self) -> Dict[str, Any]:
        """Get detailed pool statistics."""
        stats = self.get_stats().to_dict()

        try:
            # Get server info
            server_info = await self.client.server_info()
            stats.update(
                {
                    "server_version": server_info.get("version"),
                    "max_bson_object_size": server_info.get("maxBsonObjectSize"),
                    "max_message_size_bytes": server_info.get("maxMessageSizeBytes"),
                    "max_wire_version": server_info.get("maxWireVersion"),
                    "min_wire_version": server_info.get("minWireVersion"),
                }
            )
        except Exception as e:
            logger.warning(f"Failed to get MongoDB server info: {e}")

        return stats

    async def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Get collection statistics."""
        try:
            collection = self._database[collection_name]
            stats = await collection.aggregate(
                [{"$collStats": {"storageStats": True}}]
            ).to_list(length=1)

            if stats:
                return stats[0]
            return {}

        except Exception as e:
            logger.error(f"Failed to get collection stats for {collection_name}: {e}")
            return {}

    async def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            stats = await self._database.command("dbStats")
            return stats

        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}
