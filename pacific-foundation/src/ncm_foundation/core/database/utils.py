"""
Database utilities and helpers.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, TypeVar

from motor.motor_asyncio import AsyncIOMotorDatabase
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .models.base import BaseModel
from .repositories.base import AbstractRepository

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class DatabaseUtils:
    """Database utility functions."""

    @staticmethod
    async def create_tables(engine, models: List[Type[BaseModel]]) -> None:
        """Create database tables for models."""
        try:
            async with engine.begin() as conn:
                for model in models:
                    await conn.run_sync(model.metadata.create_all)
            logger.info(f"Created tables for {len(models)} models")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise

    @staticmethod
    async def drop_tables(engine, models: List[Type[BaseModel]]) -> None:
        """Drop database tables for models."""
        try:
            async with engine.begin() as conn:
                for model in models:
                    await conn.run_sync(model.metadata.drop_all)
            logger.info(f"Dropped tables for {len(models)} models")
        except Exception as e:
            logger.error(f"Failed to drop tables: {e}")
            raise

    @staticmethod
    async def execute_raw_sql(
        session: AsyncSession, sql: str, params: Optional[Dict] = None
    ) -> Any:
        """Execute raw SQL query."""
        try:
            result = await session.execute(text(sql), params or {})
            return result.fetchall()
        except Exception as e:
            logger.error(f"Failed to execute SQL: {e}")
            raise

    @staticmethod
    async def bulk_insert(
        session: AsyncSession, model_class: Type[T], data_list: List[Dict[str, Any]]
    ) -> List[T]:
        """Bulk insert entities."""
        try:
            instances = [model_class(**data) for data in data_list]
            session.add_all(instances)
            await session.commit()

            # Refresh all instances
            for instance in instances:
                await session.refresh(instance)

            return instances
        except Exception as e:
            await session.rollback()
            logger.error(f"Bulk insert failed: {e}")
            raise

    @staticmethod
    async def bulk_update(
        session: AsyncSession, model_class: Type[T], updates: List[Dict[str, Any]]
    ) -> int:
        """Bulk update entities."""
        try:
            updated_count = 0
            for update_data in updates:
                id = update_data.pop("id")
                result = await session.execute(
                    session.query(model_class)
                    .filter(model_class.id == id)
                    .update(update_data)
                )
                updated_count += result.rowcount
            await session.commit()
            return updated_count
        except Exception as e:
            await session.rollback()
            logger.error(f"Bulk update failed: {e}")
            raise

    @staticmethod
    async def bulk_delete(
        session: AsyncSession, model_class: Type[T], ids: List[int]
    ) -> int:
        """Bulk delete entities."""
        try:
            result = await session.execute(
                session.query(model_class).filter(model_class.id.in_(ids)).delete()
            )
            await session.commit()
            return result.rowcount
        except Exception as e:
            await session.rollback()
            logger.error(f"Bulk delete failed: {e}")
            raise


class MongoDBUtils:
    """MongoDB utility functions."""

    @staticmethod
    async def create_indexes(
        database: AsyncIOMotorDatabase,
        collection_name: str,
        indexes: List[Dict[str, Any]],
    ) -> None:
        """Create indexes on MongoDB collection."""
        try:
            collection = database[collection_name]
            for index in indexes:
                await collection.create_index(list(index.items()))
            logger.info(
                f"Created {len(indexes)} indexes for collection {collection_name}"
            )
        except Exception as e:
            logger.error(f"Failed to create indexes for {collection_name}: {e}")
            raise

    @staticmethod
    async def create_text_index(
        database: AsyncIOMotorDatabase, collection_name: str, fields: List[str]
    ) -> None:
        """Create text index for full-text search."""
        try:
            collection = database[collection_name]
            text_fields = {field: "text" for field in fields}
            await collection.create_index(list(text_fields.items()))
            logger.info(f"Created text index for collection {collection_name}")
        except Exception as e:
            logger.error(f"Failed to create text index for {collection_name}: {e}")
            raise

    @staticmethod
    async def aggregate_data(
        database: AsyncIOMotorDatabase,
        collection_name: str,
        pipeline: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Execute aggregation pipeline."""
        try:
            collection = database[collection_name]
            cursor = collection.aggregate(pipeline)
            return await cursor.to_list(length=None)
        except Exception as e:
            logger.error(f"Aggregation failed for {collection_name}: {e}")
            raise


class DatabaseValidator:
    """Database validation utilities."""

    @staticmethod
    async def validate_connection(session: AsyncSession) -> bool:
        """Validate database connection."""
        try:
            await session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Connection validation failed: {e}")
            return False

    @staticmethod
    async def validate_table_exists(session: AsyncSession, table_name: str) -> bool:
        """Validate table exists."""
        try:
            result = await session.execute(text(f"SELECT 1 FROM {table_name} LIMIT 1"))
            return result.fetchone() is not None
        except Exception as e:
            logger.error(f"Table validation failed for {table_name}: {e}")
            return False

    @staticmethod
    async def validate_mongodb_collection(
        database: AsyncIOMotorDatabase, collection_name: str
    ) -> bool:
        """Validate MongoDB collection exists."""
        try:
            collections = await database.list_collection_names()
            return collection_name in collections
        except Exception as e:
            logger.error(f"Collection validation failed for {collection_name}: {e}")
            return False


class DatabaseMigrator:
    """Database migration utilities."""

    @staticmethod
    async def backup_table(
        session: AsyncSession, table_name: str, backup_table: str
    ) -> bool:
        """Backup table data."""
        try:
            # Create backup table
            await session.execute(
                text(f"CREATE TABLE {backup_table} AS SELECT * FROM {table_name}")
            )
            await session.commit()
            logger.info(f"Backed up table {table_name} to {backup_table}")
            return True
        except Exception as e:
            await session.rollback()
            logger.error(f"Backup failed for {table_name}: {e}")
            return False

    @staticmethod
    async def restore_table(
        session: AsyncSession, table_name: str, backup_table: str
    ) -> bool:
        """Restore table from backup."""
        try:
            # Clear target table
            await session.execute(text(f"DELETE FROM {table_name}"))

            # Restore from backup
            await session.execute(
                text(f"INSERT INTO {table_name} SELECT * FROM {backup_table}")
            )
            await session.commit()
            logger.info(f"Restored table {table_name} from {backup_table}")
            return True
        except Exception as e:
            await session.rollback()
            logger.error(f"Restore failed for {table_name}: {e}")
            return False

    @staticmethod
    async def migrate_data(
        session: AsyncSession,
        source_table: str,
        target_table: str,
        field_mapping: Dict[str, str],
    ) -> int:
        """Migrate data between tables with field mapping."""
        try:
            # Build field list
            source_fields = list(field_mapping.keys())
            target_fields = list(field_mapping.values())

            # Build migration query
            field_list = ", ".join(source_fields)
            target_field_list = ", ".join(target_fields)

            query = f"""
            INSERT INTO {target_table} ({target_field_list})
            SELECT {field_list} FROM {source_table}
            """

            result = await session.execute(text(query))
            await session.commit()

            logger.info(f"Migrated data from {source_table} to {target_table}")
            return result.rowcount
        except Exception as e:
            await session.rollback()
            logger.error(f"Data migration failed: {e}")
            raise


class DatabaseMonitor:
    """Database monitoring utilities."""

    @staticmethod
    async def get_table_stats(session: AsyncSession, table_name: str) -> Dict[str, Any]:
        """Get table statistics."""
        try:
            # Get row count
            count_result = await session.execute(
                text(f"SELECT COUNT(*) FROM {table_name}")
            )
            row_count = count_result.scalar()

            # Get table size (PostgreSQL specific)
            size_result = await session.execute(
                text(
                    f"""
                SELECT pg_size_pretty(pg_total_relation_size('{table_name}')) as size
            """
                )
            )
            table_size = size_result.scalar()

            return {
                "table_name": table_name,
                "row_count": row_count,
                "table_size": table_size,
                "timestamp": datetime.utcnow(),
            }
        except Exception as e:
            logger.error(f"Failed to get table stats for {table_name}: {e}")
            return {}

    @staticmethod
    async def get_connection_stats(session: AsyncSession) -> Dict[str, Any]:
        """Get connection statistics."""
        try:
            # Get active connections
            conn_result = await session.execute(
                text(
                    """
                SELECT count(*) as active_connections 
                FROM pg_stat_activity 
                WHERE state = 'active'
            """
                )
            )
            active_connections = conn_result.scalar()

            # Get database size
            size_result = await session.execute(
                text(
                    """
                SELECT pg_size_pretty(pg_database_size(current_database())) as db_size
            """
                )
            )
            db_size = size_result.scalar()

            return {
                "active_connections": active_connections,
                "database_size": db_size,
                "timestamp": datetime.utcnow(),
            }
        except Exception as e:
            logger.error(f"Failed to get connection stats: {e}")
            return {}
