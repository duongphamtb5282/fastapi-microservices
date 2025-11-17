# Database Migrations for NCM-Foundation

A comprehensive migration system for ncm-foundation that supports multiple database types with Docker integration, following the approach from the [Medium article on SQLAlchemy migrations with Alembic and Docker](https://medium.com/@johnidouglasmarangon/using-migrations-in-python-sqlalchemy-with-alembic-docker-solution-bd79b219d6a6).

## Features

- **Multi-Database Support**: PostgreSQL, MySQL, SQLite, and MongoDB
- **Alembic Integration**: Full SQLAlchemy migration support
- **Docker Support**: Containerized migrations for microservices
- **Migration Types**: Schema, data, index, and seed migrations
- **Rollback Support**: Safe migration rollback capabilities
- **Validation**: Comprehensive migration validation
- **Backup/Restore**: Automatic database backup before migrations
- **CLI Tools**: Easy-to-use command-line interface

## Quick Start

### 1. Installation

```bash
pip install ncm-foundation
```

### 2. Basic Usage

```python
from ncm_foundation.core.database.migrations import (
    MigrationRunner, MigrationConfig, MigrationType
)

# Configure migration
config = MigrationConfig(
    database_url="postgresql+asyncpg://user:password@localhost/database",
    database_type="postgresql",
    migration_directory="migrations"
)

# Create runner
runner = MigrationRunner(config)
await runner.initialize()

# Run migrations
results = await runner.run_migrations()
```

### 3. CLI Usage

```bash
# Run migrations
python -m migrations.runner run --database postgresql

# Create new migration
python -m migrations.runner create "Add user table" --type schema

# Rollback migration
python -m migrations.runner rollback --version 001_add_users_table

# Check status
python -m migrations.runner status
```

## Architecture

### Core Components

1. **Migration Manager**: Handles migration execution and tracking
2. **Database Providers**: SQLAlchemy and MongoDB support
3. **Migration Runner**: CLI and programmatic interface
4. **Validation Utils**: Migration validation and testing
5. **Docker Support**: Containerized migration execution

### File Structure

```
migrations/
├── __init__.py                 # Main exports
├── manager.py                  # Core migration manager
├── config.py                  # Configuration classes
├── runner.py                  # Migration runner
├── sqlalchemy_manager.py      # SQLAlchemy migration manager
├── mongodb_manager.py         # MongoDB migration manager
├── utils/                     # Migration utilities
│   ├── database_utils.py     # Database utilities
│   ├── migration_utils.py    # Migration utilities
│   └── validation_utils.py    # Validation utilities
├── docker/                    # Docker support
│   ├── Dockerfile.migration   # Migration container
│   ├── docker-compose.migration.yml
│   └── migration-entrypoint.sh
└── README.md                  # This file
```

## Configuration

### Environment Variables

```bash
# Database configuration
MIGRATION_DATABASE_URL=postgresql+asyncpg://user:password@localhost/database
MIGRATION_DATABASE_TYPE=postgresql

# Migration settings
MIGRATION_MIGRATION_DIRECTORY=migrations
MIGRATION_BACKUP_BEFORE_MIGRATION=true
MIGRATION_AUTO_ROLLBACK_ON_FAILURE=true

# Docker settings
MIGRATION_DOCKER_ENABLED=false
MIGRATION_DOCKER_IMAGE=ncm-migration:latest

# Security settings
MIGRATION_ENCRYPTION_KEY=your_encryption_key
MIGRATION_AUDIT_ENABLED=true
```

### Configuration File

```python
# migration_config.py
from ncm_foundation.core.database.migrations import MigrationConfig, MigrationEnvironment

config = MigrationConfig(
    database_url="postgresql+asyncpg://user:password@localhost/database",
    database_type="postgresql",
    migration_directory="migrations",
    backup_before_migration=True,
    auto_rollback_on_failure=True,
    environment=MigrationEnvironment.PRODUCTION,
    docker_enabled=True
)
```

## Migration Types

### 1. Schema Migrations

Schema migrations handle database structure changes.

```python
# Create schema migration
version = await runner.create_migration(
    "Add user table with audit fields",
    MigrationType.SCHEMA
)

# Migration file will be created with:
# - Table creation
# - Column modifications
# - Index creation
# - Constraint changes
```

### 2. Data Migrations

Data migrations handle data transformations.

```python
# Create data migration
version = await runner.create_migration(
    "Migrate user data to new format",
    MigrationType.DATA
)

# Migration file will include:
# - Data transformation logic
# - Data validation
# - Rollback procedures
```

### 3. Index Migrations

Index migrations handle database indexes.

```python
# Create index migration
version = await runner.create_migration(
    "Add performance indexes",
    MigrationType.INDEX
)

# Migration file will include:
# - Index creation
# - Index optimization
# - Index cleanup
```

### 4. Seed Migrations

Seed migrations handle initial data.

```python
# Create seed migration
version = await runner.create_migration(
    "Seed initial user roles",
    MigrationType.SEED
)

# Migration file will include:
# - Initial data insertion
# - Data validation
# - Duplicate prevention
```

## Database Support

### PostgreSQL

```python
config = MigrationConfig(
    database_url="postgresql+asyncpg://user:password@localhost/database",
    database_type="postgresql"
)

# Features:
# - Full SQLAlchemy support
# - Alembic integration
# - Row-level security
# - Advanced indexing
```

### MySQL

```python
config = MigrationConfig(
    database_url="mysql+aiomysql://user:password@localhost/database",
    database_type="mysql"
)

# Features:
# - MySQL-specific optimizations
# - Character set handling
# - Engine selection
```

### SQLite

```python
config = MigrationConfig(
    database_url="sqlite+aiosqlite:///database.db",
    database_type="sqlite"
)

# Features:
# - File-based database
# - Development-friendly
# - Limited concurrent access
```

### MongoDB

```python
config = MigrationConfig(
    database_url="mongodb://user:password@localhost/database",
    database_type="mongodb"
)

# Features:
# - Document-based operations
# - Collection management
# - Index creation
# - Data aggregation
```

## Docker Support

### 1. Build Migration Image

```bash
# Build migration image
docker build -f migrations/docker/Dockerfile.migration -t ncm-migration:latest .
```

### 2. Run Migrations in Docker

```bash
# Run migrations
docker-compose -f migrations/docker/docker-compose.migration.yml up migration

# Run specific migration
docker run --rm \
  -e DATABASE_URL="postgresql://user:password@host:port/database" \
  -e TARGET_VERSION="001_add_users_table" \
  ncm-migration:latest run --target-version 001_add_users_table
```

### 3. Docker Compose Configuration

```yaml
# docker-compose.migration.yml
version: "3.8"

services:
  migration:
    build:
      context: .
      dockerfile: migrations/docker/Dockerfile.migration
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - MIGRATION_ENVIRONMENT=${MIGRATION_ENVIRONMENT}
    volumes:
      - ./migrations:/app/migrations
    networks:
      - ncm-network
    depends_on:
      - postgres
      - mongodb
```

## Migration Lifecycle

### 1. Create Migration

```bash
# Create new migration
python -m migrations.runner create "Add user table" --type schema

# This creates:
# - Migration file with timestamp
# - Template with required functions
# - Metadata file
```

### 2. Edit Migration

```python
# Edit migration file
def upgrade() -> None:
    """Add user table."""
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(100), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade() -> None:
    """Remove user table."""
    op.drop_table('users')
```

### 3. Run Migration

```bash
# Run all pending migrations
python -m migrations.runner run

# Run specific migration
python -m migrations.runner run --target-version 001_add_users_table

# Dry run
python -m migrations.runner run --dry-run
```

### 4. Validate Migration

```bash
# Validate all migrations
python -m migrations.runner validate

# Check migration status
python -m migrations.runner status
```

### 5. Rollback Migration

```bash
# Rollback specific migration
python -m migrations.runner rollback --version 001_add_users_table
```

## Advanced Features

### 1. Migration Dependencies

```python
# Set migration dependencies
migration.add_dependency("001_create_users_table")
migration.add_dependency("002_create_roles_table")
```

### 2. Custom Migration Logic

```python
class CustomMigration(AbstractMigration):
    async def up(self, session):
        # Custom upgrade logic
        await session.execute("CREATE INDEX idx_users_email ON users(email)")

    async def down(self, session):
        # Custom rollback logic
        await session.execute("DROP INDEX idx_users_email")

    async def validate(self, session):
        # Custom validation
        result = await session.execute("SELECT COUNT(*) FROM users")
        return result.scalar() > 0
```

### 3. Data Migration with Validation

```python
async def upgrade_data():
    """Migrate user data."""
    # Get all users
    users = await session.execute("SELECT * FROM users")

    for user in users:
        # Transform data
        new_data = transform_user_data(user)

        # Update user
        await session.execute(
            "UPDATE users SET data = :data WHERE id = :id",
            {"data": new_data, "id": user.id}
        )

    # Validate migration
    await validate_user_data(session)
```

### 4. Backup and Restore

```python
# Automatic backup before migration
config = MigrationConfig(
    backup_before_migration=True,
    backup_directory="backups"
)

# Manual backup
await runner.backup_database("backup_20240101.sql")

# Restore from backup
await runner.restore_database("backup_20240101.sql")
```

## Best Practices

### 1. Migration Naming

```bash
# Use descriptive names
python -m migrations.runner create "Add user table with audit fields"

# Use consistent format
YYYYMMDD_HHMMSS_description.py
```

### 2. Migration Ordering

```python
# Set dependencies
migration.add_dependency("001_create_users_table")
migration.add_dependency("002_create_roles_table")
```

### 3. Rollback Safety

```python
def downgrade() -> None:
    """Safe rollback."""
    # Check if data exists before dropping
    result = op.get_bind().execute("SELECT COUNT(*) FROM users")
    if result.scalar() == 0:
        op.drop_table('users')
    else:
        raise Exception("Cannot drop table with data")
```

### 4. Data Validation

```python
async def validate(self, session):
    """Validate migration result."""
    # Check table exists
    result = await session.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'users'
        )
    """)

    if not result.scalar():
        return False

    # Check data integrity
    result = await session.execute("SELECT COUNT(*) FROM users")
    return result.scalar() >= 0
```

## Troubleshooting

### 1. Migration Failures

```bash
# Check migration status
python -m migrations.runner status

# View error logs
tail -f migration.log

# Rollback failed migration
python -m migrations.runner rollback --version failed_migration
```

### 2. Database Connection Issues

```python
# Test database connection
from ncm_foundation.core.database.migrations.utils import DatabaseUtils

# Validate connection
is_connected = await DatabaseUtils.validate_database_connection(provider)

# Test environment
results = await DatabaseUtils.test_migration_environment(provider)
```

### 3. Docker Issues

```bash
# Check container logs
docker logs migration-container

# Debug container
docker exec -it migration-container bash

# Rebuild image
docker build --no-cache -f migrations/docker/Dockerfile.migration -t ncm-migration:latest .
```

## Examples

### Complete Migration Example

```python
from ncm_foundation.core.database.migrations import (
    MigrationRunner, MigrationConfig, MigrationType
)

async def run_migrations():
    # Configure migration
    config = MigrationConfig(
        database_url="postgresql+asyncpg://user:password@localhost/database",
        database_type="postgresql",
        migration_directory="migrations",
        backup_before_migration=True,
        auto_rollback_on_failure=True
    )

    # Create runner
    runner = MigrationRunner(config)
    await runner.initialize()

    try:
        # Create migration
        version = await runner.create_migration(
            "Add user table with audit fields",
            MigrationType.SCHEMA
        )
        print(f"Created migration: {version}")

        # Run migrations
        results = await runner.run_migrations()

        # Check results
        for result in results:
            print(f"{result['version']}: {result['status']}")

        # Validate migrations
        is_valid = await runner.validate_migrations()
        print(f"All migrations valid: {is_valid}")

    finally:
        await runner.close()

# Run migrations
import asyncio
asyncio.run(run_migrations())
```

### Docker Migration Example

```bash
#!/bin/bash
# Run migrations in Docker

# Build migration image
docker build -f migrations/docker/Dockerfile.migration -t ncm-migration:latest .

# Run migrations
docker run --rm \
  -e DATABASE_URL="postgresql://user:password@host:port/database" \
  -e MIGRATION_ENVIRONMENT="production" \
  -v $(pwd)/migrations:/app/migrations \
  ncm-migration:latest run

# Rollback migration
docker run --rm \
  -e DATABASE_URL="postgresql://user:password@host:port/database" \
  -v $(pwd)/migrations:/app/migrations \
  ncm-migration:latest rollback --version 001_add_users_table
```

## Support

For questions, issues, or contributions:

1. Check the troubleshooting section
2. Review the examples
3. Create an issue in the repository
4. Check the main project documentation

## License

This migration system is part of the ncm-foundation project and follows the same license terms.
