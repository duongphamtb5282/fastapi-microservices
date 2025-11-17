"""
Database migration manager with multi-database support.
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Type

logger = logging.getLogger(__name__)


class MigrationStatus(Enum):
    """Migration status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class MigrationType(Enum):
    """Migration type enumeration."""

    SCHEMA = "schema"
    DATA = "data"
    INDEX = "index"
    SEED = "seed"
    CUSTOM = "custom"


class MigrationRecord:
    """Migration record for tracking."""

    def __init__(
        self,
        version: str,
        description: str,
        migration_type: MigrationType,
        status: MigrationStatus,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        error_message: Optional[str] = None,
        rollback_version: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.version = version
        self.description = description
        self.migration_type = migration_type
        self.status = status
        self.started_at = started_at
        self.completed_at = completed_at
        self.error_message = error_message
        self.rollback_version = rollback_version
        self.dependencies = dependencies or []
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert record to dictionary."""
        return {
            "version": self.version,
            "description": self.description,
            "migration_type": self.migration_type.value,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "error_message": self.error_message,
            "rollback_version": self.rollback_version,
            "dependencies": self.dependencies,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MigrationRecord":
        """Create record from dictionary."""
        return cls(
            version=data["version"],
            description=data["description"],
            migration_type=MigrationType(data["migration_type"]),
            status=MigrationStatus(data["status"]),
            started_at=(
                datetime.fromisoformat(data["started_at"])
                if data.get("started_at")
                else None
            ),
            completed_at=(
                datetime.fromisoformat(data["completed_at"])
                if data.get("completed_at")
                else None
            ),
            error_message=data.get("error_message"),
            rollback_version=data.get("rollback_version"),
            dependencies=data.get("dependencies", []),
            metadata=data.get("metadata", {}),
        )


class AbstractMigration(ABC):
    """Abstract migration class."""

    def __init__(self, version: str, description: str, migration_type: MigrationType):
        self.version = version
        self.description = description
        self.migration_type = migration_type
        self.dependencies: List[str] = []
        self.rollback_version: Optional[str] = None
        self.metadata: Dict[str, Any] = {}

    @abstractmethod
    async def up(self, session: Any) -> None:
        """Run migration forward."""
        pass

    @abstractmethod
    async def down(self, session: Any) -> None:
        """Rollback migration."""
        pass

    @abstractmethod
    async def validate(self, session: Any) -> bool:
        """Validate migration result."""
        pass

    def add_dependency(self, version: str) -> None:
        """Add migration dependency."""
        if version not in self.dependencies:
            self.dependencies.append(version)

    def set_rollback_version(self, version: str) -> None:
        """Set rollback version."""
        self.rollback_version = version

    def set_metadata(self, key: str, value: Any) -> None:
        """Set migration metadata."""
        self.metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get migration metadata."""
        return self.metadata.get(key, default)


class DatabaseMigrationManager:
    """Database migration manager with multi-database support."""

    def __init__(self, provider, migration_table: str = "migration_history"):
        self.provider = provider
        self.migration_table = migration_table
        self.migrations: List[AbstractMigration] = []
        self.logger = logging.getLogger(__name__)
        self._setup_migration_table()

    def _setup_migration_table(self) -> None:
        """Setup migration tracking table."""
        # This will be implemented by subclasses
        pass

    def register_migration(self, migration: AbstractMigration) -> None:
        """Register a migration."""
        self.migrations.append(migration)
        self.migrations.sort(key=lambda x: x.version)
        self.logger.info(
            f"Registered migration: {migration.version} - {migration.description}"
        )

    async def run_migrations(
        self,
        target_version: Optional[str] = None,
        migration_type: Optional[MigrationType] = None,
        dry_run: bool = False,
    ) -> List[MigrationRecord]:
        """Run all pending migrations."""
        records = []

        self.logger.info(f"Starting migration process (dry_run={dry_run})")

        for migration in self.migrations:
            if target_version and migration.version > target_version:
                break

            if migration_type and migration.migration_type != migration_type:
                continue

            # Check dependencies
            if not await self._check_dependencies(migration):
                self.logger.warning(
                    f"Skipping {migration.version} due to unmet dependencies"
                )
                continue

            record = await self._run_single_migration(migration, dry_run)
            records.append(record)

            if record.status == MigrationStatus.FAILED:
                self.logger.error(
                    f"Migration {migration.version} failed, stopping execution"
                )
                break

        self.logger.info(
            f"Migration process completed. {len(records)} migration(s) processed"
        )
        return records

    async def rollback_migration(self, version: str) -> bool:
        """Rollback specific migration."""
        migration = next((m for m in self.migrations if m.version == version), None)
        if not migration:
            self.logger.error(f"Migration {version} not found")
            return False

        try:
            self.logger.info(f"Rolling back migration: {version}")
            async with self.provider.get_session() as session:
                await migration.down(session)
                await self._record_migration_rollback(version)
            self.logger.info(f"Successfully rolled back migration: {version}")
            return True
        except Exception as e:
            self.logger.error(f"Rollback {version} failed: {e}")
            return False

    async def get_migration_status(self) -> List[MigrationRecord]:
        """Get migration status."""
        try:
            async with self.provider.get_session() as session:
                return await self._get_migration_records(session)
        except Exception as e:
            self.logger.error(f"Failed to get migration status: {e}")
            return []

    async def validate_migrations(self) -> bool:
        """Validate all migrations."""
        try:
            for migration in self.migrations:
                async with self.provider.get_session() as session:
                    if not await migration.validate(session):
                        self.logger.error(
                            f"Migration {migration.version} validation failed"
                        )
                        return False
            return True
        except Exception as e:
            self.logger.error(f"Migration validation failed: {e}")
            return False

    async def _run_single_migration(
        self, migration: AbstractMigration, dry_run: bool = False
    ) -> MigrationRecord:
        """Run a single migration."""
        record = MigrationRecord(
            version=migration.version,
            description=migration.description,
            migration_type=migration.migration_type,
            status=MigrationStatus.PENDING,
        )

        try:
            # Check if migration already applied
            if await self._is_migration_applied(migration.version):
                record.status = MigrationStatus.COMPLETED
                self.logger.info(f"Migration {migration.version} already applied")
                return record

            if dry_run:
                record.status = MigrationStatus.COMPLETED
                self.logger.info(f"Dry run: Would apply migration {migration.version}")
                return record

            # Run migration
            record.status = MigrationStatus.RUNNING
            record.started_at = datetime.utcnow()

            async with self.provider.get_session() as session:
                await migration.up(session)

                # Validate migration
                if await migration.validate(session):
                    record.status = MigrationStatus.COMPLETED
                    record.completed_at = datetime.utcnow()
                    await self._record_migration(migration.version, record)
                    self.logger.info(
                        f"Successfully applied migration: {migration.version}"
                    )
                else:
                    raise Exception("Migration validation failed")

        except Exception as e:
            record.status = MigrationStatus.FAILED
            record.error_message = str(e)
            record.completed_at = datetime.utcnow()
            self.logger.error(f"Migration {migration.version} failed: {e}")

        return record

    async def _check_dependencies(self, migration: AbstractMigration) -> bool:
        """Check if migration dependencies are met."""
        for dep_version in migration.dependencies:
            if not await self._is_migration_applied(dep_version):
                return False
        return True

    async def _is_migration_applied(self, version: str) -> bool:
        """Check if migration is already applied."""
        try:
            async with self.provider.get_session() as session:
                records = await self._get_migration_records(session)
                for record in records:
                    if (
                        record.version == version
                        and record.status == MigrationStatus.COMPLETED
                    ):
                        return True
                return False
        except Exception as e:
            self.logger.error(f"Failed to check migration status: {e}")
            return False

    async def _record_migration(self, version: str, record: MigrationRecord) -> None:
        """Record migration in database."""
        # This will be implemented by subclasses
        pass

    async def _record_migration_rollback(self, version: str) -> None:
        """Record migration rollback in database."""
        # This will be implemented by subclasses
        pass

    async def _get_migration_records(self, session: Any) -> List[MigrationRecord]:
        """Get migration records from database."""
        # This will be implemented by subclasses
        return []

    def get_migration_summary(self) -> Dict[str, Any]:
        """Get migration summary."""
        total_migrations = len(self.migrations)
        applied_migrations = 0
        pending_migrations = 0

        for migration in self.migrations:
            if asyncio.run(self._is_migration_applied(migration.version)):
                applied_migrations += 1
            else:
                pending_migrations += 1

        return {
            "total_migrations": total_migrations,
            "applied_migrations": applied_migrations,
            "pending_migrations": pending_migrations,
            "migrations": [
                {
                    "version": m.version,
                    "description": m.description,
                    "type": m.migration_type.value,
                    "dependencies": m.dependencies,
                }
                for m in self.migrations
            ],
        }
