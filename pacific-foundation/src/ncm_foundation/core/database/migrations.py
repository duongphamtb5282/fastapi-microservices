"""
Database migration management system.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .interfaces import MigrationManager, MigrationStatus

logger = logging.getLogger(__name__)


class AlembicMigrationManager(MigrationManager):
    """Alembic-based migration manager."""

    def __init__(
        self,
        provider: Any,
        migrations_path: str = "migrations",
        alembic_config_path: Optional[str] = None,
    ):
        self.provider = provider
        self.migrations_path = Path(migrations_path)
        self.alembic_config_path = alembic_config_path or str(
            self.migrations_path / "alembic.ini"
        )
        self._migration_history: List[MigrationStatus] = []

    async def run_migrations(
        self, target_version: Optional[str] = None
    ) -> List[MigrationStatus]:
        """Run database migrations."""
        try:
            import alembic
            from alembic import command
            from alembic.config import Config

            # Configure Alembic
            alembic_cfg = Config(self.alembic_config_path)

            # Run migrations
            if target_version:
                command.upgrade(alembic_cfg, target_version)
            else:
                command.upgrade(alembic_cfg, "head")

            # Get migration status
            await self._load_migration_history()

            logger.info(f"Migrations completed up to {target_version or 'head'}")
            return self._migration_history

        except Exception as e:
            logger.error(f"Failed to run migrations: {e}")
            raise

    async def rollback_migration(self, version: str) -> bool:
        """Rollback a specific migration."""
        try:
            import alembic
            from alembic import command
            from alembic.config import Config

            # Configure Alembic
            alembic_cfg = Config(self.alembic_config_path)

            # Rollback migration
            command.downgrade(alembic_cfg, version)

            # Reload migration history
            await self._load_migration_history()

            logger.info(f"Migration rolled back to version: {version}")
            return True

        except Exception as e:
            logger.error(f"Failed to rollback migration {version}: {e}")
            return False

    async def get_migration_status(self) -> List[MigrationStatus]:
        """Get migration status."""
        await self._load_migration_history()
        return self._migration_history.copy()

    async def create_migration(self, name: str, description: str) -> str:
        """Create a new migration."""
        try:
            import alembic
            from alembic import command
            from alembic.config import Config

            # Configure Alembic
            alembic_cfg = Config(self.alembic_config_path)

            # Create migration
            message = f"{name}: {description}"
            command.revision(alembic_cfg, message=message, autogenerate=True)

            # Get the latest migration file
            versions_path = self.migrations_path / "alembic" / "versions"
            migration_files = list(versions_path.glob("*.py"))
            latest_migration = max(migration_files, key=lambda f: f.stat().st_mtime)

            logger.info(f"Created migration: {latest_migration.name}")
            return str(latest_migration)

        except Exception as e:
            logger.error(f"Failed to create migration: {e}")
            raise

    async def _load_migration_history(self) -> None:
        """Load migration history from database."""
        try:
            # Query migration history from database
            query = """
                SELECT version_num, description, applied_at
                FROM alembic_version
                ORDER BY applied_at DESC
            """

            results = await self.provider.execute_query(query)

            self._migration_history = []
            for result in results:
                status = MigrationStatus(
                    version=result["version_num"],
                    description=result["description"],
                    applied=True,
                    applied_at=result["applied_at"],
                )
                self._migration_history.append(status)

        except Exception as e:
            logger.warning(f"Failed to load migration history: {e}")
            self._migration_history = []


class MongoMigrationManager(MigrationManager):
    """MongoDB migration manager."""

    def __init__(self, provider: Any, migrations_path: str = "migrations"):
        self.provider = provider
        self.migrations_path = Path(migrations_path)
        self.collection_name = "migration_history"
        self._migration_history: List[MigrationStatus] = []

    async def run_migrations(
        self, target_version: Optional[str] = None
    ) -> List[MigrationStatus]:
        """Run MongoDB migrations."""
        try:
            # Get migration files
            migration_files = self._get_migration_files()

            # Get applied migrations
            applied_migrations = await self._get_applied_migrations()
            applied_versions = {m["version"] for m in applied_migrations}

            # Run pending migrations
            for migration_file in migration_files:
                version = migration_file.stem

                if version in applied_versions:
                    continue

                if target_version and version > target_version:
                    break

                await self._run_migration_file(migration_file)
                await self._record_migration(version, migration_file.name)

            # Reload migration history
            await self._load_migration_history()

            logger.info("MongoDB migrations completed")
            return self._migration_history

        except Exception as e:
            logger.error(f"Failed to run MongoDB migrations: {e}")
            raise

    async def rollback_migration(self, version: str) -> bool:
        """Rollback a specific migration."""
        try:
            # Find migration file
            migration_file = self.migrations_path / f"{version}.py"
            if not migration_file.exists():
                logger.error(f"Migration file not found: {migration_file}")
                return False

            # Run rollback function if exists
            await self._run_migration_rollback(migration_file)

            # Remove from applied migrations
            await self._remove_migration_record(version)

            # Reload migration history
            await self._load_migration_history()

            logger.info(f"MongoDB migration rolled back: {version}")
            return True

        except Exception as e:
            logger.error(f"Failed to rollback MongoDB migration {version}: {e}")
            return False

    async def get_migration_status(self) -> List[MigrationStatus]:
        """Get migration status."""
        await self._load_migration_history()
        return self._migration_history.copy()

    async def create_migration(self, name: str, description: str) -> str:
        """Create a new migration."""
        try:
            # Generate migration filename
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{name}.py"
            migration_file = self.migrations_path / filename

            # Create migration template
            template = self._get_migration_template(name, description)
            migration_file.write_text(template)

            logger.info(f"Created MongoDB migration: {filename}")
            return str(migration_file)

        except Exception as e:
            logger.error(f"Failed to create MongoDB migration: {e}")
            raise

    def _get_migration_files(self) -> List[Path]:
        """Get migration files sorted by name."""
        if not self.migrations_path.exists():
            return []

        migration_files = list(self.migrations_path.glob("*.py"))
        return sorted(migration_files, key=lambda f: f.name)

    async def _get_applied_migrations(self) -> List[Dict[str, Any]]:
        """Get applied migrations from database."""
        try:
            collection = self.provider.database[self.collection_name]
            cursor = collection.find({}).sort("applied_at", -1)
            return await cursor.to_list(length=None)
        except Exception as e:
            logger.warning(f"Failed to get applied migrations: {e}")
            return []

    async def _run_migration_file(self, migration_file: Path) -> None:
        """Run a migration file."""
        try:
            # Import and execute migration
            import importlib.util

            spec = importlib.util.spec_from_file_location("migration", migration_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if hasattr(module, "upgrade"):
                await module.upgrade(self.provider)
            else:
                logger.warning(
                    f"Migration {migration_file.name} has no upgrade function"
                )

        except Exception as e:
            logger.error(f"Failed to run migration {migration_file.name}: {e}")
            raise

    async def _run_migration_rollback(self, migration_file: Path) -> None:
        """Run migration rollback."""
        try:
            import importlib.util

            spec = importlib.util.spec_from_file_location("migration", migration_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if hasattr(module, "downgrade"):
                await module.downgrade(self.provider)
            else:
                logger.warning(
                    f"Migration {migration_file.name} has no downgrade function"
                )

        except Exception as e:
            logger.error(f"Failed to rollback migration {migration_file.name}: {e}")
            raise

    async def _record_migration(self, version: str, filename: str) -> None:
        """Record migration as applied."""
        try:
            collection = self.provider.database[self.collection_name]
            await collection.insert_one(
                {
                    "version": version,
                    "filename": filename,
                    "applied_at": datetime.utcnow(),
                    "description": f"Migration {version}",
                }
            )
        except Exception as e:
            logger.error(f"Failed to record migration {version}: {e}")
            raise

    async def _remove_migration_record(self, version: str) -> None:
        """Remove migration record."""
        try:
            collection = self.provider.database[self.collection_name]
            await collection.delete_one({"version": version})
        except Exception as e:
            logger.error(f"Failed to remove migration record {version}: {e}")
            raise

    async def _load_migration_history(self) -> None:
        """Load migration history."""
        try:
            applied_migrations = await self._get_applied_migrations()

            self._migration_history = []
            for migration in applied_migrations:
                status = MigrationStatus(
                    version=migration["version"],
                    description=migration.get("description", ""),
                    applied=True,
                    applied_at=migration["applied_at"],
                )
                self._migration_history.append(status)

        except Exception as e:
            logger.warning(f"Failed to load migration history: {e}")
            self._migration_history = []

    def _get_migration_template(self, name: str, description: str) -> str:
        """Get migration template."""
        return f'''"""
{description}
"""

import asyncio
from datetime import datetime


async def upgrade(provider):
    """Upgrade database schema."""
    # Add your upgrade logic here
    pass


async def downgrade(provider):
    """Downgrade database schema."""
    # Add your downgrade logic here
    pass


if __name__ == "__main__":
    # For testing migrations
    asyncio.run(upgrade(None))
'''
