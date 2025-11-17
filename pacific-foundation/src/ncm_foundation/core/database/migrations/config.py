"""
Migration configuration module.
"""

from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from pydantic import BaseSettings
except ImportError:
    from pydantic_settings import BaseSettings

from pydantic import Field


class MigrationEnvironment(Enum):
    """Migration environment enumeration."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class MigrationConfig(BaseSettings):
    """Migration configuration settings."""

    # Database configuration
    database_url: str = Field(..., description="Database connection URL")
    database_type: str = Field(
        ..., description="Database type (postgresql, mysql, mongodb)"
    )

    # Migration settings
    migration_table: str = Field(
        default="migration_history", description="Migration tracking table"
    )
    migration_directory: str = Field(
        default="migrations", description="Migration directory"
    )
    migration_template_directory: str = Field(
        default="templates", description="Template directory"
    )

    # Alembic configuration
    alembic_config_path: str = Field(
        default="alembic.ini", description="Alembic config path"
    )
    alembic_script_location: str = Field(
        default="alembic", description="Alembic script location"
    )

    # Docker configuration
    docker_enabled: bool = Field(
        default=False, description="Enable Docker migration support"
    )
    docker_image: str = Field(
        default="ncm-migration:latest", description="Migration Docker image"
    )
    docker_network: str = Field(default="ncm-network", description="Docker network")
    docker_volume: str = Field(
        default="ncm-migrations", description="Docker volume for migrations"
    )

    # Migration behavior
    auto_rollback_on_failure: bool = Field(
        default=True, description="Auto rollback on failure"
    )
    validate_migrations: bool = Field(
        default=True, description="Validate migrations before running"
    )
    backup_before_migration: bool = Field(
        default=True, description="Backup before migration"
    )
    backup_directory: str = Field(default="backups", description="Backup directory")

    # Environment-specific settings
    environment: MigrationEnvironment = Field(default=MigrationEnvironment.DEVELOPMENT)
    dry_run: bool = Field(default=False, description="Dry run mode")
    verbose: bool = Field(default=False, description="Verbose logging")

    # Security settings
    encryption_key: Optional[str] = Field(
        default=None, description="Migration encryption key"
    )
    audit_enabled: bool = Field(default=True, description="Enable migration auditing")

    # Performance settings
    batch_size: int = Field(default=1000, description="Batch size for data migrations")
    timeout: int = Field(default=3600, description="Migration timeout in seconds")
    retry_attempts: int = Field(default=3, description="Number of retry attempts")
    retry_delay: int = Field(default=5, description="Delay between retries in seconds")

    # Notification settings
    notification_enabled: bool = Field(
        default=False, description="Enable migration notifications"
    )
    notification_webhook: Optional[str] = Field(
        default=None, description="Webhook URL for notifications"
    )
    notification_email: Optional[str] = Field(
        default=None, description="Email for notifications"
    )

    class Config:
        env_prefix = "MIGRATION_"
        case_sensitive = False

    def get_migration_path(self) -> Path:
        """Get migration directory path."""
        return Path(self.migration_directory)

    def get_template_path(self) -> Path:
        """Get template directory path."""
        return self.get_migration_path() / self.migration_template_directory

    def get_backup_path(self) -> Path:
        """Get backup directory path."""
        return Path(self.backup_directory)

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == MigrationEnvironment.PRODUCTION

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == MigrationEnvironment.DEVELOPMENT

    def should_backup(self) -> bool:
        """Check if backup should be performed."""
        return self.backup_before_migration and not self.dry_run

    def should_validate(self) -> bool:
        """Check if validation should be performed."""
        return self.validate_migrations and not self.dry_run

    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration."""
        return {
            "url": self.database_url,
            "type": self.database_type,
            "migration_table": self.migration_table,
        }

    def get_alembic_config(self) -> Dict[str, Any]:
        """Get Alembic configuration."""
        return {
            "config_path": self.alembic_config_path,
            "script_location": self.alembic_script_location,
        }

    def get_docker_config(self) -> Dict[str, Any]:
        """Get Docker configuration."""
        return {
            "enabled": self.docker_enabled,
            "image": self.docker_image,
            "network": self.docker_network,
            "volume": self.docker_volume,
        }

    def get_notification_config(self) -> Dict[str, Any]:
        """Get notification configuration."""
        return {
            "enabled": self.notification_enabled,
            "webhook": self.notification_webhook,
            "email": self.notification_email,
        }

    def validate_config(self) -> List[str]:
        """Validate configuration and return any errors."""
        errors = []

        # Validate database URL
        if not self.database_url:
            errors.append("Database URL is required")

        # Validate database type
        valid_types = ["postgresql", "mysql", "sqlite", "mongodb"]
        if self.database_type not in valid_types:
            errors.append(f"Database type must be one of: {', '.join(valid_types)}")

        # Validate migration directory
        migration_path = self.get_migration_path()
        if not migration_path.exists():
            errors.append(f"Migration directory does not exist: {migration_path}")

        # Validate Alembic config for SQL databases
        if self.database_type in ["postgresql", "mysql", "sqlite"]:
            alembic_config_path = Path(self.alembic_config_path)
            if not alembic_config_path.exists():
                errors.append(
                    f"Alembic config file does not exist: {alembic_config_path}"
                )

        # Validate Docker config if enabled
        if self.docker_enabled:
            if not self.docker_image:
                errors.append("Docker image is required when Docker is enabled")

        # Validate notification config
        if self.notification_enabled:
            if not self.notification_webhook and not self.notification_email:
                errors.append(
                    "Notification webhook or email is required when notifications are enabled"
                )

        return errors
