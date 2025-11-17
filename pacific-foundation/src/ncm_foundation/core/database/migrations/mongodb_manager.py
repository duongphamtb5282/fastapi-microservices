"""
MongoDB migration manager.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from .config import MigrationConfig
from .manager import (
    DatabaseMigrationManager,
    MigrationRecord,
    MigrationStatus,
    MigrationType,
)

logger = logging.getLogger(__name__)


class MongoMigrationManager(DatabaseMigrationManager):
    """MongoDB migration manager."""

    def __init__(self, provider, config: MigrationConfig):
        super().__init__(provider, config.migration_table)
        self.config = config
        self.migration_collection = config.migration_table
        self._setup_migration_table()

    def _setup_migration_table(self) -> None:
        """Setup migration tracking collection."""
        # MongoDB collections are created automatically
        pass

    async def create_migration(
        self, message: str, migration_type: MigrationType = MigrationType.SCHEMA
    ) -> str:
        """Create new MongoDB migration."""
        try:
            version = self._generate_version()

            migration_template = {
                "version": version,
                "description": message,
                "migration_type": migration_type.value,
                "created_at": datetime.utcnow(),
                "status": MigrationStatus.PENDING.value,
                "operations": [],
                "dependencies": [],
                "metadata": {},
            }

            # Save migration template
            await self._save_migration_template(version, migration_template)

            logger.info(f"Created MongoDB migration: {version}")
            return version
        except Exception as e:
            logger.error(f"Failed to create MongoDB migration: {e}")
            raise

    async def run_mongo_migrations(self, target_version: Optional[str] = None) -> None:
        """Run MongoDB migrations."""
        try:
            async with self.provider.get_session() as database:
                migrations = await self._get_pending_migrations(
                    database, target_version
                )

                for migration in migrations:
                    await self._execute_mongo_migration(database, migration)

            logger.info("Successfully ran MongoDB migrations")
        except Exception as e:
            logger.error(f"MongoDB migration failed: {e}")
            raise

    async def rollback_mongo_migration(self, version: str) -> None:
        """Rollback MongoDB migration."""
        try:
            async with self.provider.get_session() as database:
                migration = await self._get_migration_by_version(database, version)
                if migration:
                    await self._execute_mongo_rollback(database, migration)
                    await self._record_migration_rollback(version)

            logger.info(f"Successfully rolled back MongoDB migration: {version}")
        except Exception as e:
            logger.error(f"MongoDB rollback failed: {e}")
            raise

    async def _execute_mongo_migration(
        self, database: AsyncIOMotorDatabase, migration: Dict[str, Any]
    ) -> None:
        """Execute MongoDB migration."""
        try:
            operations = migration.get("operations", [])

            for operation in operations:
                await self._execute_operation(database, operation)

            # Record successful migration
            await self._record_migration_success(migration["version"])

        except Exception as e:
            # Record failed migration
            await self._record_migration_failure(migration["version"], str(e))
            raise

    async def _execute_mongo_rollback(
        self, database: AsyncIOMotorDatabase, migration: Dict[str, Any]
    ) -> None:
        """Execute MongoDB rollback."""
        try:
            rollback_operations = migration.get("rollback_operations", [])

            for operation in rollback_operations:
                await self._execute_operation(database, operation)

        except Exception as e:
            logger.error(f"Failed to execute rollback operation: {e}")
            raise

    async def _execute_operation(
        self, database: AsyncIOMotorDatabase, operation: Dict[str, Any]
    ) -> None:
        """Execute migration operation."""
        op_type = operation.get("type")
        collection = operation.get("collection")
        data = operation.get("data", {})

        try:
            if op_type == "create_collection":
                await database.create_collection(collection, **data)
                logger.debug(f"Created collection: {collection}")

            elif op_type == "drop_collection":
                await database.drop_collection(collection)
                logger.debug(f"Dropped collection: {collection}")

            elif op_type == "create_index":
                await database[collection].create_index(
                    data["keys"], **data.get("options", {})
                )
                logger.debug(f"Created index on {collection}: {data['keys']}")

            elif op_type == "drop_index":
                await database[collection].drop_index(data["name"])
                logger.debug(f"Dropped index on {collection}: {data['name']}")

            elif op_type == "insert_data":
                documents = data["documents"]
                if documents:
                    await database[collection].insert_many(documents)
                    logger.debug(
                        f"Inserted {len(documents)} documents into {collection}"
                    )

            elif op_type == "update_data":
                result = await database[collection].update_many(
                    data["filter"], data["update"]
                )
                logger.debug(
                    f"Updated {result.modified_count} documents in {collection}"
                )

            elif op_type == "delete_data":
                result = await database[collection].delete_many(data["filter"])
                logger.debug(
                    f"Deleted {result.deleted_count} documents from {collection}"
                )

            elif op_type == "aggregate_data":
                pipeline = data["pipeline"]
                result = (
                    await database[collection].aggregate(pipeline).to_list(length=None)
                )
                logger.debug(f"Aggregated {len(result)} documents from {collection}")

            else:
                logger.warning(f"Unknown operation type: {op_type}")

        except Exception as e:
            logger.error(f"Failed to execute operation {op_type}: {e}")
            raise

    async def _get_pending_migrations(
        self, database: AsyncIOMotorDatabase, target_version: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get pending migrations."""
        try:
            # Get all migrations
            migrations_cursor = (
                database[self.migration_collection]
                .find(
                    {
                        "status": {
                            "$in": [
                                MigrationStatus.PENDING.value,
                                MigrationStatus.FAILED.value,
                            ]
                        }
                    }
                )
                .sort("created_at", 1)
            )

            migrations = await migrations_cursor.to_list(length=None)

            # Filter by target version if specified
            if target_version:
                migrations = [m for m in migrations if m["version"] <= target_version]

            return migrations
        except Exception as e:
            logger.error(f"Failed to get pending migrations: {e}")
            return []

    async def _get_migration_by_version(
        self, database: AsyncIOMotorDatabase, version: str
    ) -> Optional[Dict[str, Any]]:
        """Get migration by version."""
        try:
            return await database[self.migration_collection].find_one(
                {"version": version}
            )
        except Exception as e:
            logger.error(f"Failed to get migration {version}: {e}")
            return None

    async def _save_migration_template(
        self, version: str, template: Dict[str, Any]
    ) -> None:
        """Save migration template."""
        try:
            async with self.provider.get_session() as database:
                await database[self.migration_collection].insert_one(template)
        except Exception as e:
            logger.error(f"Failed to save migration template: {e}")
            raise

    async def _record_migration_success(self, version: str) -> None:
        """Record successful migration."""
        try:
            async with self.provider.get_session() as database:
                await database[self.migration_collection].update_one(
                    {"version": version},
                    {
                        "$set": {
                            "status": MigrationStatus.COMPLETED.value,
                            "completed_at": datetime.utcnow(),
                        }
                    },
                )
        except Exception as e:
            logger.error(f"Failed to record migration success: {e}")
            raise

    async def _record_migration_failure(self, version: str, error_message: str) -> None:
        """Record failed migration."""
        try:
            async with self.provider.get_session() as database:
                await database[self.migration_collection].update_one(
                    {"version": version},
                    {
                        "$set": {
                            "status": MigrationStatus.FAILED.value,
                            "error_message": error_message,
                            "completed_at": datetime.utcnow(),
                        }
                    },
                )
        except Exception as e:
            logger.error(f"Failed to record migration failure: {e}")
            raise

    async def _record_migration(self, version: str, record: MigrationRecord) -> None:
        """Record migration in database."""
        try:
            async with self.provider.get_session() as database:
                await database[self.migration_collection].update_one(
                    {"version": version},
                    {
                        "$set": {
                            "version": record.version,
                            "description": record.description,
                            "migration_type": record.migration_type.value,
                            "status": record.status.value,
                            "started_at": record.started_at,
                            "completed_at": record.completed_at,
                            "error_message": record.error_message,
                            "rollback_version": record.rollback_version,
                            "dependencies": record.dependencies,
                            "metadata": record.metadata,
                        }
                    },
                    upsert=True,
                )
        except Exception as e:
            logger.error(f"Failed to record migration: {e}")
            raise

    async def _record_migration_rollback(self, version: str) -> None:
        """Record migration rollback in database."""
        try:
            async with self.provider.get_session() as database:
                await database[self.migration_collection].update_one(
                    {"version": version},
                    {
                        "$set": {
                            "status": MigrationStatus.ROLLED_BACK.value,
                            "completed_at": datetime.utcnow(),
                        }
                    },
                )
        except Exception as e:
            logger.error(f"Failed to record migration rollback: {e}")
            raise

    async def _get_migration_records(
        self, database: AsyncIOMotorDatabase
    ) -> List[MigrationRecord]:
        """Get migration records from database."""
        try:
            cursor = database[self.migration_collection].find().sort("created_at", 1)
            documents = await cursor.to_list(length=None)

            records = []
            for doc in documents:
                record = MigrationRecord(
                    version=doc["version"],
                    description=doc["description"],
                    migration_type=MigrationType(doc["migration_type"]),
                    status=MigrationStatus(doc["status"]),
                    started_at=doc.get("started_at"),
                    completed_at=doc.get("completed_at"),
                    error_message=doc.get("error_message"),
                    rollback_version=doc.get("rollback_version"),
                    dependencies=doc.get("dependencies", []),
                    metadata=doc.get("metadata", {}),
                )
                records.append(record)

            return records
        except Exception as e:
            logger.error(f"Failed to get migration records: {e}")
            return []

    def _generate_version(self) -> str:
        """Generate migration version."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return f"{timestamp}"

    async def backup_database(self, backup_path: str) -> bool:
        """Backup MongoDB database."""
        try:
            import os
            import subprocess

            # Create backup directory if it doesn't exist
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)

            # MongoDB backup
            result = subprocess.run(
                [
                    "mongodump",
                    "--uri",
                    self.config.database_url,
                    "--out",
                    backup_path,
                    "--verbose",
                ],
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                logger.info(f"MongoDB backup created: {backup_path}")
                return True
            else:
                logger.error(f"MongoDB backup failed: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"MongoDB backup failed: {e}")
            return False

    async def restore_database(self, backup_path: str) -> bool:
        """Restore MongoDB database."""
        try:
            import subprocess

            # MongoDB restore
            result = subprocess.run(
                [
                    "mongorestore",
                    "--uri",
                    self.config.database_url,
                    backup_path,
                    "--verbose",
                ],
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                logger.info(f"MongoDB restored from: {backup_path}")
                return True
            else:
                logger.error(f"MongoDB restore failed: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"MongoDB restore failed: {e}")
            return False
