"""
Database utilities for migrations.
"""

import asyncio
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DatabaseUtils:
    """Database utilities for migrations."""

    @staticmethod
    async def backup_database(provider, backup_path: str) -> bool:
        """Backup database before migration."""
        try:
            # Create backup directory if it doesn't exist
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)

            if hasattr(provider, "get_engine"):  # SQLAlchemy
                return await DatabaseUtils._backup_sql_database(provider, backup_path)
            else:  # MongoDB
                return await DatabaseUtils._backup_mongo_database(provider, backup_path)

        except Exception as e:
            logger.error(f"Database backup failed: {e}")
            return False

    @staticmethod
    async def restore_database(provider, backup_path: str) -> bool:
        """Restore database from backup."""
        try:
            if hasattr(provider, "get_engine"):  # SQLAlchemy
                return await DatabaseUtils._restore_sql_database(provider, backup_path)
            else:  # MongoDB
                return await DatabaseUtils._restore_mongo_database(
                    provider, backup_path
                )

        except Exception as e:
            logger.error(f"Database restore failed: {e}")
            return False

    @staticmethod
    async def _backup_sql_database(provider, backup_path: str) -> bool:
        """Backup SQL database."""
        try:
            # Extract database connection details
            db_url = (
                provider.config.database_url
                if hasattr(provider.config, "database_url")
                else str(provider.config)
            )

            if "postgresql" in db_url:
                # PostgreSQL backup
                result = subprocess.run(
                    [
                        "pg_dump",
                        db_url,
                        "-f",
                        backup_path,
                        "--verbose",
                        "--no-password",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=300,
                )

                if result.returncode == 0:
                    logger.info(f"PostgreSQL backup created: {backup_path}")
                    return True
                else:
                    logger.error(f"PostgreSQL backup failed: {result.stderr}")
                    return False

            elif "mysql" in db_url:
                # MySQL backup
                result = subprocess.run(
                    ["mysqldump", db_url, "--result-file", backup_path, "--verbose"],
                    capture_output=True,
                    text=True,
                    timeout=300,
                )

                if result.returncode == 0:
                    logger.info(f"MySQL backup created: {backup_path}")
                    return True
                else:
                    logger.error(f"MySQL backup failed: {result.stderr}")
                    return False

            elif "sqlite" in db_url:
                # SQLite backup
                import shutil

                shutil.copy2(db_url.replace("sqlite:///", ""), backup_path)
                logger.info(f"SQLite backup created: {backup_path}")
                return True
            else:
                logger.warning(f"Backup not supported for database type: {db_url}")
                return True

        except Exception as e:
            logger.error(f"SQL database backup failed: {e}")
            return False

    @staticmethod
    async def _backup_mongo_database(provider, backup_path: str) -> bool:
        """Backup MongoDB database."""
        try:
            # Extract database connection details
            db_url = (
                provider.config.database_url
                if hasattr(provider.config, "database_url")
                else str(provider.config)
            )

            result = subprocess.run(
                ["mongodump", "--uri", db_url, "--out", backup_path, "--verbose"],
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

    @staticmethod
    async def _restore_sql_database(provider, backup_path: str) -> bool:
        """Restore SQL database."""
        try:
            db_url = (
                provider.config.database_url
                if hasattr(provider.config, "database_url")
                else str(provider.config)
            )

            if "postgresql" in db_url:
                # PostgreSQL restore
                result = subprocess.run(
                    ["psql", db_url, "-f", backup_path, "--verbose"],
                    capture_output=True,
                    text=True,
                    timeout=300,
                )

                if result.returncode == 0:
                    logger.info(f"PostgreSQL restored from: {backup_path}")
                    return True
                else:
                    logger.error(f"PostgreSQL restore failed: {result.stderr}")
                    return False

            elif "mysql" in db_url:
                # MySQL restore
                result = subprocess.run(
                    ["mysql", db_url, "<", backup_path],
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=300,
                )

                if result.returncode == 0:
                    logger.info(f"MySQL restored from: {backup_path}")
                    return True
                else:
                    logger.error(f"MySQL restore failed: {result.stderr}")
                    return False

            elif "sqlite" in db_url:
                # SQLite restore
                import shutil

                shutil.copy2(backup_path, db_url.replace("sqlite:///", ""))
                logger.info(f"SQLite restored from: {backup_path}")
                return True
            else:
                logger.warning(f"Restore not supported for database type: {db_url}")
                return True

        except Exception as e:
            logger.error(f"SQL database restore failed: {e}")
            return False

    @staticmethod
    async def _restore_mongo_database(provider, backup_path: str) -> bool:
        """Restore MongoDB database."""
        try:
            db_url = (
                provider.config.database_url
                if hasattr(provider.config, "database_url")
                else str(provider.config)
            )

            result = subprocess.run(
                ["mongorestore", "--uri", db_url, backup_path, "--verbose"],
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

    @staticmethod
    async def validate_database_connection(provider) -> bool:
        """Validate database connection."""
        try:
            if hasattr(provider, "health_check"):
                return await provider.health_check()
            return True
        except Exception as e:
            logger.error(f"Database connection validation failed: {e}")
            return False

    @staticmethod
    async def get_database_info(provider) -> Dict[str, Any]:
        """Get database information."""
        try:
            info = {
                "type": provider.__class__.__name__,
                "connected": (
                    provider.is_connected
                    if hasattr(provider, "is_connected")
                    else False
                ),
            }

            if hasattr(provider, "get_stats"):
                stats = await provider.get_stats()
                info.update(stats)

            return info
        except Exception as e:
            logger.error(f"Failed to get database info: {e}")
            return {}

    @staticmethod
    async def test_migration_environment(provider) -> Dict[str, bool]:
        """Test migration environment."""
        results = {
            "connection": False,
            "permissions": False,
            "backup": False,
            "restore": False,
        }

        try:
            # Test connection
            results["connection"] = await DatabaseUtils.validate_database_connection(
                provider
            )

            # Test permissions (create/delete test table/collection)
            results["permissions"] = await DatabaseUtils._test_permissions(provider)

            # Test backup/restore
            test_backup_path = (
                f"/tmp/test_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            )
            results["backup"] = await DatabaseUtils.backup_database(
                provider, test_backup_path
            )

            if results["backup"]:
                results["restore"] = await DatabaseUtils.restore_database(
                    provider, test_backup_path
                )
                # Cleanup test backup
                import shutil

                if os.path.exists(test_backup_path):
                    shutil.rmtree(test_backup_path)

        except Exception as e:
            logger.error(f"Environment test failed: {e}")

        return results

    @staticmethod
    async def _test_permissions(provider) -> bool:
        """Test database permissions."""
        try:
            if hasattr(provider, "get_engine"):  # SQLAlchemy
                async with provider.get_session() as session:
                    # Test table creation
                    await session.execute(
                        "CREATE TABLE IF NOT EXISTS test_migration_permissions (id INT)"
                    )
                    await session.execute(
                        "DROP TABLE IF EXISTS test_migration_permissions"
                    )
                    await session.commit()
                    return True
            else:  # MongoDB
                async with provider.get_session() as database:
                    # Test collection creation
                    test_collection = database["test_migration_permissions"]
                    await test_collection.insert_one({"test": True})
                    await test_collection.drop()
                    return True
        except Exception as e:
            logger.error(f"Permission test failed: {e}")
            return False

    @staticmethod
    def get_backup_filename(database_type: str) -> str:
        """Get backup filename based on database type."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        if database_type == "postgresql":
            return f"postgresql_backup_{timestamp}.sql"
        elif database_type == "mysql":
            return f"mysql_backup_{timestamp}.sql"
        elif database_type == "sqlite":
            return f"sqlite_backup_{timestamp}.db"
        elif database_type == "mongodb":
            return f"mongodb_backup_{timestamp}"
        else:
            return f"database_backup_{timestamp}"

    @staticmethod
    def cleanup_old_backups(backup_directory: str, keep_days: int = 7) -> int:
        """Cleanup old backup files."""
        try:
            backup_path = Path(backup_directory)
            if not backup_path.exists():
                return 0

            cutoff_date = datetime.utcnow().timestamp() - (keep_days * 24 * 60 * 60)
            deleted_count = 0

            for file_path in backup_path.iterdir():
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_date:
                    file_path.unlink()
                    deleted_count += 1
                elif file_path.is_dir() and file_path.stat().st_mtime < cutoff_date:
                    import shutil

                    shutil.rmtree(file_path)
                    deleted_count += 1

            logger.info(f"Cleaned up {deleted_count} old backup files")
            return deleted_count

        except Exception as e:
            logger.error(f"Backup cleanup failed: {e}")
            return 0
