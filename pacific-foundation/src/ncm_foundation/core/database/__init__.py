"""
Database foundation module with multi-database support.

This module provides:
- Abstract database providers for SQL and NoSQL databases
- Connection pooling for performance
- Entity listeners for audit fields
- Database security features
- Repository pattern with multi-database support
"""

from .config import DatabaseConfig, DatabaseSettings, DatabaseType
from .models.base import AuditMixin, BaseModel, SoftDeleteMixin, TimestampMixin
from .pooling.base import AbstractConnectionPool
from .providers.base import AbstractDatabaseProvider
from .providers.mongodb_provider import MongoDBProvider
from .providers.sqlalchemy_provider import SQLAlchemyProvider
from .repositories.base import AbstractRepository
from .repositories.mongodb_repo import MongoDBRepository
from .repositories.sqlalchemy_repo import SQLAlchemyRepository
from .schemas.base import AuditSchema, BaseSchema, SoftDeleteSchema
from .security.access_control import RowLevelSecurity, SecurityLevel
from .security.audit_logging import SecurityAuditLogger
from .security.encryption import EncryptedString
from .session import DatabaseManager

__all__ = [
    # Configuration
    "DatabaseConfig",
    "DatabaseType",
    "DatabaseSettings",
    # Providers
    "AbstractDatabaseProvider",
    "SQLAlchemyProvider",
    "MongoDBProvider",
    # Models
    "BaseModel",
    "TimestampMixin",
    "AuditMixin",
    "SoftDeleteMixin",
    # Schemas
    "BaseSchema",
    "AuditSchema",
    "SoftDeleteSchema",
    # Repositories
    "AbstractRepository",
    "SQLAlchemyRepository",
    "MongoDBRepository",
    # Pooling
    "AbstractConnectionPool",
    # Security
    "EncryptedString",
    "RowLevelSecurity",
    "SecurityLevel",
    "SecurityAuditLogger",
    # Manager
    "DatabaseManager",
]
