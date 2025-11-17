"""
SQLAlchemy migration manager with Alembic integration.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    text,
)
from sqlalchemy.ext.asyncio import AsyncSession

from .config import MigrationConfig
from .manager import (
    DatabaseMigrationManager,
    MigrationRecord,
    MigrationStatus,
    MigrationType,
)

logger = logging.getLogger(__name__)


class SQLAlchemyMigrationManager(DatabaseMigrationManager):
    """SQLAlchemy migration manager with Alembic integration."""

    def __init__(self, provider, config: MigrationConfig):
        super().__init__(provider, config.migration_table)
        self.config = config
        self.alembic_config = Config(config.alembic_config_path)
        self.script_dir = ScriptDirectory.from_config(self.alembic_config)
        self._setup_migration_table()

    def _setup_migration_table(self) -> None:
        """Setup migration tracking table."""
        # Create migration table if it doesn't exist
        asyncio.run(self._create_migration_table())

    async def _create_migration_table(self) -> None:
        """Create migration tracking table."""
        try:
            async with self.provider.get_session() as session:
                # Check if table exists
                result = await session.execute(
                    text(
                        """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = :table_name
                    )
                """
                    ),
                    {"table_name": self.migration_table},
                )

                if not result.scalar():
                    # Create migration table
                    await session.execute(
                        text(
                            f"""
                        CREATE TABLE {self.migration_table} (
                            id SERIAL PRIMARY KEY,
                            version VARCHAR(50) UNIQUE NOT NULL,
                            description TEXT,
                            migration_type VARCHAR(20) NOT NULL,
                            status VARCHAR(20) NOT NULL,
                            started_at TIMESTAMP,
                            completed_at TIMESTAMP,
                            error_message TEXT,
                            rollback_version VARCHAR(50),
                            dependencies JSONB,
                            metadata JSONB,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """
                        )
                    )
                    await session.commit()
                    logger.info(f"Created migration table: {self.migration_table}")
        except Exception as e:
            logger.error(f"Failed to create migration table: {e}")
            raise

    async def create_migration(
        self,
        message: str,
        migration_type: MigrationType = MigrationType.SCHEMA,
        autogenerate: bool = True,
    ) -> str:
        """Create new migration using Alembic."""
        try:
            # Generate migration file
            revision = command.revision(
                self.alembic_config, message=message, autogenerate=autogenerate
            )

            # Customize migration based on type
            await self._customize_migration(revision, migration_type)

            logger.info(f"Created migration: {revision}")
            return revision
        except Exception as e:
            logger.error(f"Failed to create migration: {e}")
            raise

    async def run_alembic_migrations(self, target_revision: str = "head") -> None:
        """Run Alembic migrations."""
        try:
            command.upgrade(self.alembic_config, target_revision)
            logger.info(f"Successfully ran Alembic migrations to {target_revision}")
        except Exception as e:
            logger.error(f"Alembic migration failed: {e}")
            raise

    async def rollback_alembic_migration(self, target_revision: str) -> None:
        """Rollback Alembic migration."""
        try:
            command.downgrade(self.alembic_config, target_revision)
            logger.info(
                f"Successfully rolled back Alembic migration to {target_revision}"
            )
        except Exception as e:
            logger.error(f"Alembic rollback failed: {e}")
            raise

    async def get_current_revision(self) -> str:
        """Get current database revision."""
        try:
            with self.provider.get_engine().connect() as connection:
                context = MigrationContext.configure(connection)
                return context.get_current_revision()
        except Exception as e:
            logger.error(f"Failed to get current revision: {e}")
            return None

    async def get_migration_history(self) -> List[Dict[str, Any]]:
        """Get migration history from Alembic."""
        try:
            with self.provider.get_engine().connect() as connection:
                context = MigrationContext.configure(connection)
                return context.get_current_heads()
        except Exception as e:
            logger.error(f"Failed to get migration history: {e}")
            return []

    async def _customize_migration(
        self, revision: str, migration_type: MigrationType
    ) -> None:
        """Customize migration file based on type."""
        try:
            # Get migration file path
            migration_file = self.script_dir.get_revision(revision).path

            # Read migration file
            with open(migration_file, "r") as f:
                content = f.read()

            # Customize based on migration type
            if migration_type == MigrationType.DATA:
                content = self._add_data_migration_helpers(content)
            elif migration_type == MigrationType.INDEX:
                content = self._add_index_migration_helpers(content)
            elif migration_type == MigrationType.SEED:
                content = self._add_seed_migration_helpers(content)

            # Write customized content
            with open(migration_file, "w") as f:
                f.write(content)

        except Exception as e:
            logger.error(f"Failed to customize migration: {e}")
            raise

    def _add_data_migration_helpers(self, content: str) -> str:
        """Add data migration helper functions."""
        helpers = '''
# Data migration helpers
def upgrade_data():
    """Upgrade data."""
    pass

def downgrade_data():
    """Downgrade data."""
    pass

def validate_data():
    """Validate data migration."""
    pass
'''
        return content.replace(
            "def downgrade() -> None:", helpers + "\ndef downgrade() -> None:"
        )

    def _add_index_migration_helpers(self, content: str) -> str:
        """Add index migration helper functions."""
        helpers = '''
# Index migration helpers
def upgrade_indexes():
    """Upgrade indexes."""
    pass

def downgrade_indexes():
    """Downgrade indexes."""
    pass
'''
        return content.replace(
            "def downgrade() -> None:", helpers + "\ndef downgrade() -> None:"
        )

    def _add_seed_migration_helpers(self, content: str) -> str:
        """Add seed migration helper functions."""
        helpers = '''
# Seed migration helpers
def seed_data():
    """Seed data."""
    pass

def unseed_data():
    """Unseed data."""
    pass
'''
        return content.replace(
            "def downgrade() -> None:", helpers + "\ndef downgrade() -> None:"
        )

    async def _record_migration(self, version: str, record: MigrationRecord) -> None:
        """Record migration in database."""
        try:
            async with self.provider.get_session() as session:
                await session.execute(
                    text(
                        f"""
                    INSERT INTO {self.migration_table} 
                    (version, description, migration_type, status, started_at, completed_at, 
                     error_message, rollback_version, dependencies, metadata)
                    VALUES (:version, :description, :migration_type, :status, :started_at, :completed_at,
                            :error_message, :rollback_version, :dependencies, :metadata)
                    ON CONFLICT (version) DO UPDATE SET
                        status = EXCLUDED.status,
                        started_at = EXCLUDED.started_at,
                        completed_at = EXCLUDED.completed_at,
                        error_message = EXCLUDED.error_message
                """
                    ),
                    {
                        "version": record.version,
                        "description": record.description,
                        "migration_type": record.migration_type.value,
                        "status": record.status.value,
                        "started_at": record.started_at,
                        "completed_at": record.completed_at,
                        "error_message": record.error_message,
                        "rollback_version": record.rollback_version,
                        "dependencies": json.dumps(record.dependencies),
                        "metadata": json.dumps(record.metadata),
                    },
                )
                await session.commit()
        except Exception as e:
            logger.error(f"Failed to record migration: {e}")
            raise

    async def _record_migration_rollback(self, version: str) -> None:
        """Record migration rollback in database."""
        try:
            async with self.provider.get_session() as session:
                await session.execute(
                    text(
                        f"""
                    UPDATE {self.migration_table} 
                    SET status = :status, completed_at = :completed_at
                    WHERE version = :version
                """
                    ),
                    {
                        "version": version,
                        "status": MigrationStatus.ROLLED_BACK.value,
                        "completed_at": datetime.utcnow(),
                    },
                )
                await session.commit()
        except Exception as e:
            logger.error(f"Failed to record migration rollback: {e}")
            raise

    async def _get_migration_records(
        self, session: AsyncSession
    ) -> List[MigrationRecord]:
        """Get migration records from database."""
        try:
            result = await session.execute(
                text(
                    f"""
                SELECT version, description, migration_type, status, started_at, completed_at,
                       error_message, rollback_version, dependencies, metadata
                FROM {self.migration_table}
                ORDER BY created_at
            """
                )
            )

            records = []
            for row in result.fetchall():
                record = MigrationRecord(
                    version=row.version,
                    description=row.description,
                    migration_type=MigrationType(row.migration_type),
                    status=MigrationStatus(row.status),
                    started_at=row.started_at,
                    completed_at=row.completed_at,
                    error_message=row.error_message,
                    rollback_version=row.rollback_version,
                    dependencies=(
                        json.loads(row.dependencies) if row.dependencies else []
                    ),
                    metadata=json.loads(row.metadata) if row.metadata else {},
                )
                records.append(record)

            return records
        except Exception as e:
            logger.error(f"Failed to get migration records: {e}")
            return []

    async def backup_database(self, backup_path: str) -> bool:
        """Backup database before migration."""
        try:
            import os
            import subprocess

            # Create backup directory if it doesn't exist
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)

            # Extract database connection details
            db_url = self.config.database_url
            if db_url.startswith("postgresql"):
                # PostgreSQL backup
                result = subprocess.run(
                    ["pg_dump", db_url, "-f", backup_path, "--verbose"],
                    capture_output=True,
                    text=True,
                    timeout=300,
                )

                if result.returncode == 0:
                    logger.info(f"Database backup created: {backup_path}")
                    return True
                else:
                    logger.error(f"Database backup failed: {result.stderr}")
                    return False
            else:
                logger.warning(
                    f"Backup not supported for database type: {self.config.database_type}"
                )
                return True

        except Exception as e:
            logger.error(f"Database backup failed: {e}")
            return False

    async def restore_database(self, backup_path: str) -> bool:
        """Restore database from backup."""
        try:
            import subprocess

            db_url = self.config.database_url
            if db_url.startswith("postgresql"):
                # PostgreSQL restore
                result = subprocess.run(
                    ["psql", db_url, "-f", backup_path, "--verbose"],
                    capture_output=True,
                    text=True,
                    timeout=300,
                )

                if result.returncode == 0:
                    logger.info(f"Database restored from: {backup_path}")
                    return True
                else:
                    logger.error(f"Database restore failed: {result.stderr}")
                    return False
            else:
                logger.warning(
                    f"Restore not supported for database type: {self.config.database_type}"
                )
                return True

        except Exception as e:
            logger.error(f"Database restore failed: {e}")
            return False
