"""
Database system interfaces and abstractions.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class DatabaseType(Enum):
    """Database type enumeration."""

    POSTGRESQL = "postgresql"
    MONGODB = "mongodb"
    MYSQL = "mysql"
    SQLITE = "sqlite"


class DatabaseConfig:
    """Database configuration."""

    def __init__(
        self,
        db_type: DatabaseType,
        host: str = "localhost",
        port: int = 5432,
        database: str = "ncm",
        username: str = "postgres",
        password: str = "",
        pool_size: int = 10,
        max_overflow: int = 20,
        pool_timeout: int = 30,
        pool_recycle: int = 3600,
        pool_pre_ping: bool = True,
        echo: bool = False,
        **kwargs,
    ):
        self.db_type = db_type
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        self.pool_pre_ping = pool_pre_ping
        self.echo = echo
        self.extra_params = kwargs


class DatabaseProvider(ABC):
    """Abstract database provider interface."""

    @abstractmethod
    async def connect(self) -> None:
        """Connect to database."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from database."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check database health."""
        pass

    @abstractmethod
    async def execute_query(self, query: str, params: Optional[Dict] = None) -> Any:
        """Execute a query."""
        pass

    @abstractmethod
    async def execute_transaction(self, operations: List[Dict]) -> Any:
        """Execute multiple operations in a transaction."""
        pass

    @abstractmethod
    async def get_connection(self) -> Any:
        """Get a database connection."""
        pass

    @abstractmethod
    async def return_connection(self, connection: Any) -> None:
        """Return a database connection to the pool."""
        pass


class Transaction(ABC):
    """Abstract transaction interface."""

    @abstractmethod
    async def commit(self) -> None:
        """Commit the transaction."""
        pass

    @abstractmethod
    async def rollback(self) -> None:
        """Rollback the transaction."""
        pass

    @abstractmethod
    async def savepoint(self, name: str) -> "Savepoint":
        """Create a savepoint."""
        pass


class Savepoint(ABC):
    """Abstract savepoint interface."""

    @abstractmethod
    async def commit(self) -> None:
        """Commit the savepoint."""
        pass

    @abstractmethod
    async def rollback(self) -> None:
        """Rollback the savepoint."""
        pass


class BaseEntity:
    """Base entity class with audit fields."""

    def __init__(
        self,
        id: Optional[Any] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        created_by: Optional[str] = None,
        updated_by: Optional[str] = None,
        version: int = 1,
    ):
        self.id = id
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.created_by = created_by
        self.updated_by = updated_by
        self.version = version

    def to_dict(self) -> Dict[str, Any]:
        """Convert entity to dictionary."""
        return {
            "id": self.id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "created_by": self.created_by,
            "updated_by": self.updated_by,
            "version": self.version,
        }

    def update_audit_fields(self, user_id: str) -> None:
        """Update audit fields."""
        self.updated_at = datetime.utcnow()
        self.updated_by = user_id
        self.version += 1


class AuditLogger(ABC):
    """Abstract audit logger interface."""

    @abstractmethod
    async def log_create(self, entity: BaseEntity, user_id: str) -> None:
        """Log entity creation."""
        pass

    @abstractmethod
    async def log_update(self, entity: BaseEntity, changes: Dict, user_id: str) -> None:
        """Log entity update."""
        pass

    @abstractmethod
    async def log_delete(self, entity: BaseEntity, user_id: str) -> None:
        """Log entity deletion."""
        pass


class BaseRepository(ABC):
    """Abstract base repository interface."""

    @abstractmethod
    async def create(self, entity: BaseEntity) -> BaseEntity:
        """Create entity."""
        pass

    @abstractmethod
    async def get_by_id(self, id: Any) -> Optional[BaseEntity]:
        """Get entity by ID."""
        pass

    @abstractmethod
    async def update(self, entity: BaseEntity) -> BaseEntity:
        """Update entity."""
        pass

    @abstractmethod
    async def delete(self, id: Any) -> bool:
        """Delete entity by ID."""
        pass

    @abstractmethod
    async def list(self, limit: int = 100, offset: int = 0) -> List[BaseEntity]:
        """List entities."""
        pass

    @abstractmethod
    async def count(self) -> int:
        """Count entities."""
        pass


class MigrationStatus:
    """Migration status information."""

    def __init__(
        self,
        version: str,
        description: str,
        applied: bool,
        applied_at: Optional[datetime] = None,
    ):
        self.version = version
        self.description = description
        self.applied = applied
        self.applied_at = applied_at


class MigrationManager(ABC):
    """Abstract migration manager interface."""

    @abstractmethod
    async def run_migrations(
        self, target_version: Optional[str] = None
    ) -> List[MigrationStatus]:
        """Run database migrations."""
        pass

    @abstractmethod
    async def rollback_migration(self, version: str) -> bool:
        """Rollback a specific migration."""
        pass

    @abstractmethod
    async def get_migration_status(self) -> List[MigrationStatus]:
        """Get migration status."""
        pass

    @abstractmethod
    async def create_migration(self, name: str, description: str) -> str:
        """Create a new migration."""
        pass
