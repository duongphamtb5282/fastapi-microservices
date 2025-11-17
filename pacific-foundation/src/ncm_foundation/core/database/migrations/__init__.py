"""
Database migrations module for ncm-foundation.

This module provides:
- Multi-database migration support (SQLAlchemy, MongoDB)
- Alembic integration for SQL databases
- Docker support for containerized migrations
- Migration templates and utilities
- CLI tools for migration management
"""

from .config import MigrationConfig, MigrationEnvironment
from .manager import (
    AbstractMigration,
    DatabaseMigrationManager,
    MigrationRecord,
    MigrationStatus,
    MigrationType,
)
from .mongodb_manager import MongoMigrationManager
from .runner import MigrationRunner

# Provide Alembic-compatible alias expected by other modules
from .sqlalchemy_manager import SQLAlchemyMigrationManager
from .sqlalchemy_manager import SQLAlchemyMigrationManager as AlembicMigrationManager
from .utils.database_utils import DatabaseUtils
from .utils.migration_utils import MigrationUtils

__all__ = [
    # Core classes
    "DatabaseMigrationManager",
    "AbstractMigration",
    "MigrationRecord",
    "MigrationStatus",
    "MigrationType",
    # Database-specific managers
    "SQLAlchemyMigrationManager",
    "AlembicMigrationManager",
    "MongoMigrationManager",
    # Configuration
    "MigrationConfig",
    "MigrationEnvironment",
    # Runner
    "MigrationRunner",
    # Utilities
    "DatabaseUtils",
    "MigrationUtils",
]
