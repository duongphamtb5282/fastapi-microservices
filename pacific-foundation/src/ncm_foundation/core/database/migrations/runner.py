"""
Migration runner for executing database migrations.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import DatabaseConfig, DatabaseType
from ..providers.mongodb_provider import MongoDBProvider
from ..providers.sqlalchemy_provider import SQLAlchemyProvider
from .config import MigrationConfig, MigrationEnvironment
from .manager import MigrationStatus, MigrationType
from .mongodb_manager import MongoMigrationManager
from .sqlalchemy_manager import SQLAlchemyMigrationManager

logger = logging.getLogger(__name__)


class MigrationRunner:
    """Migration runner for executing database migrations."""

    def __init__(self, config: MigrationConfig):
        self.config = config
        self.manager = None
        self.provider = None
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Setup logging for migration runner."""
        log_level = logging.DEBUG if self.config.verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

    async def initialize(self) -> None:
        """Initialize migration runner."""
        try:
            # Create database provider
            self.provider = await self._create_provider()

            # Create migration manager
            self.manager = await self._create_manager()

            # Validate configuration
            errors = self.config.validate_config()
            if errors:
                raise ValueError(f"Configuration errors: {', '.join(errors)}")

            logger.info("Migration runner initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize migration runner: {e}")
            raise

    async def _create_provider(self):
        """Create database provider."""
        # Parse database URL to create DatabaseConfig
        db_config = self._parse_database_url()

        if self.config.database_type in ["postgresql", "mysql", "sqlite"]:
            return SQLAlchemyProvider(db_config)
        elif self.config.database_type == "mongodb":
            return MongoDBProvider(db_config)
        else:
            raise ValueError(f"Unsupported database type: {self.config.database_type}")

    async def _create_manager(self):
        """Create migration manager."""
        if self.config.database_type in ["postgresql", "mysql", "sqlite"]:
            return SQLAlchemyMigrationManager(self.provider, self.config)
        elif self.config.database_type == "mongodb":
            return MongoMigrationManager(self.provider, self.config)
        else:
            raise ValueError(f"Unsupported database type: {self.config.database_type}")

    def _parse_database_url(self) -> DatabaseConfig:
        """Parse database URL to create DatabaseConfig."""
        from urllib.parse import urlparse

        parsed = urlparse(self.config.database_url)

        if parsed.scheme.startswith("postgresql"):
            db_type = DatabaseType.POSTGRESQL
        elif parsed.scheme.startswith("mysql"):
            db_type = DatabaseType.MYSQL
        elif parsed.scheme.startswith("sqlite"):
            db_type = DatabaseType.SQLITE
        elif parsed.scheme.startswith("mongodb"):
            db_type = DatabaseType.MONGODB
        else:
            raise ValueError(f"Unsupported database scheme: {parsed.scheme}")

        return DatabaseConfig(
            db_type=db_type,
            host=parsed.hostname or "localhost",
            port=parsed.port or (5432 if db_type == DatabaseType.POSTGRESQL else 27017),
            database=parsed.path.lstrip("/") if parsed.path else "ncm",
            username=parsed.username or "",
            password=parsed.password or "",
            pool_size=self.config.batch_size,
            security_enabled=self.config.audit_enabled,
        )

    async def run_migrations(
        self,
        target_version: Optional[str] = None,
        migration_type: Optional[MigrationType] = None,
        dry_run: bool = None,
    ) -> List[Dict[str, Any]]:
        """Run database migrations."""
        if dry_run is None:
            dry_run = self.config.dry_run

        try:
            # Initialize if not already done
            if not self.manager:
                await self.initialize()

            # Backup database if configured
            if self.config.should_backup() and not dry_run:
                await self._backup_database()

            # Run migrations
            logger.info(f"Starting migration process (dry_run={dry_run})")
            records = await self.manager.run_migrations(
                target_version=target_version,
                migration_type=migration_type,
                dry_run=dry_run,
            )

            # Process results
            results = []
            for record in records:
                result = {
                    "version": record.version,
                    "description": record.description,
                    "type": record.migration_type.value,
                    "status": record.status.value,
                    "started_at": (
                        record.started_at.isoformat() if record.started_at else None
                    ),
                    "completed_at": (
                        record.completed_at.isoformat() if record.completed_at else None
                    ),
                    "error_message": record.error_message,
                }
                results.append(result)

                # Log result
                status_icon = (
                    "✅" if record.status == MigrationStatus.COMPLETED else "❌"
                )
                logger.info(
                    f"{status_icon} {record.version}: {record.description} ({record.status.value})"
                )

                if record.error_message:
                    logger.error(f"   Error: {record.error_message}")

            # Check for failures
            failed_migrations = [
                r for r in records if r.status == MigrationStatus.FAILED
            ]
            if failed_migrations and not dry_run:
                logger.error(f"{len(failed_migrations)} migration(s) failed!")

                # Auto rollback if configured
                if self.config.auto_rollback_on_failure:
                    logger.info(
                        "Auto rollback enabled, rolling back failed migrations..."
                    )
                    await self._rollback_failed_migrations(failed_migrations)

            # Send notifications if configured
            if self.config.notification_enabled:
                await self._send_notification(results)

            logger.info(
                f"Migration process completed. {len(records)} migration(s) processed"
            )
            return results

        except Exception as e:
            logger.error(f"Migration process failed: {e}")
            raise

    async def rollback_migration(self, version: str) -> bool:
        """Rollback specific migration."""
        try:
            if not self.manager:
                await self.initialize()

            logger.info(f"Rolling back migration: {version}")
            success = await self.manager.rollback_migration(version)

            if success:
                logger.info(f"Successfully rolled back migration: {version}")
            else:
                logger.error(f"Failed to rollback migration: {version}")

            return success

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False

    async def get_migration_status(self) -> List[Dict[str, Any]]:
        """Get migration status."""
        try:
            if not self.manager:
                await self.initialize()

            records = await self.manager.get_migration_status()
            return [record.to_dict() for record in records]

        except Exception as e:
            logger.error(f"Failed to get migration status: {e}")
            return []

    async def validate_migrations(self) -> bool:
        """Validate all migrations."""
        try:
            if not self.manager:
                await self.initialize()

            return await self.manager.validate_migrations()

        except Exception as e:
            logger.error(f"Migration validation failed: {e}")
            return False

    async def create_migration(
        self, message: str, migration_type: MigrationType = MigrationType.SCHEMA
    ) -> str:
        """Create new migration."""
        try:
            if not self.manager:
                await self.initialize()

            version = await self.manager.create_migration(message, migration_type)
            logger.info(f"Created migration: {version}")
            return version

        except Exception as e:
            logger.error(f"Failed to create migration: {e}")
            raise

    async def _backup_database(self) -> None:
        """Backup database before migration."""
        try:
            backup_path = (
                self.config.get_backup_path()
                / f"backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            )
            backup_path.mkdir(parents=True, exist_ok=True)

            success = await self.manager.backup_database(str(backup_path))
            if success:
                logger.info(f"Database backup created: {backup_path}")
            else:
                logger.warning("Database backup failed, continuing with migration")

        except Exception as e:
            logger.warning(f"Database backup failed: {e}")

    async def _rollback_failed_migrations(self, failed_migrations: List[Any]) -> None:
        """Rollback failed migrations."""
        for migration in failed_migrations:
            try:
                await self.manager.rollback_migration(migration.version)
                logger.info(f"Rolled back failed migration: {migration.version}")
            except Exception as e:
                logger.error(f"Failed to rollback {migration.version}: {e}")

    async def _send_notification(self, results: List[Dict[str, Any]]) -> None:
        """Send migration notification."""
        try:
            # This would integrate with notification services
            # For now, just log the notification
            logger.info("Migration notification would be sent here")

        except Exception as e:
            logger.error(f"Failed to send notification: {e}")

    async def close(self) -> None:
        """Close migration runner."""
        try:
            if self.provider:
                await self.provider.disconnect()
            logger.info("Migration runner closed")
        except Exception as e:
            logger.error(f"Failed to close migration runner: {e}")


# CLI interface
async def main():
    """Main CLI interface for migration runner."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Database Migration Runner")
    parser.add_argument(
        "command",
        choices=["run", "rollback", "status", "create", "validate"],
        help="Migration command",
    )
    parser.add_argument("--config", help="Migration config file")
    parser.add_argument("--target-version", help="Target migration version")
    parser.add_argument(
        "--type", choices=[t.value for t in MigrationType], help="Migration type filter"
    )
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    # Load configuration
    config = MigrationConfig()
    if args.config:
        # Load from file
        pass

    if args.verbose:
        config.verbose = True

    if args.dry_run:
        config.dry_run = True

    # Create runner
    runner = MigrationRunner(config)

    try:
        await runner.initialize()

        if args.command == "run":
            results = await runner.run_migrations(
                target_version=args.target_version,
                migration_type=MigrationType(args.type) if args.type else None,
                dry_run=args.dry_run,
            )

            # Check for failures
            failed = [r for r in results if r["status"] == "failed"]
            if failed:
                sys.exit(1)

        elif args.command == "rollback":
            if not args.target_version:
                print("Target version required for rollback")
                sys.exit(1)

            success = await runner.rollback_migration(args.target_version)
            if not success:
                sys.exit(1)

        elif args.command == "status":
            status = await runner.get_migration_status()
            for record in status:
                print(
                    f"{record['version']}: {record['description']} ({record['status']})"
                )

        elif args.command == "create":
            if not args.target_version:
                print("Migration description required for create")
                sys.exit(1)

            version = await runner.create_migration(
                args.target_version,
                MigrationType(args.type) if args.type else MigrationType.SCHEMA,
            )
            print(f"Created migration: {version}")

        elif args.command == "validate":
            valid = await runner.validate_migrations()
            if not valid:
                sys.exit(1)
            print("All migrations are valid")

    except Exception as e:
        logger.error(f"Migration command failed: {e}")
        sys.exit(1)

    finally:
        await runner.close()


if __name__ == "__main__":
    asyncio.run(main())
