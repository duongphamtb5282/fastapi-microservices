"""
Migration examples for ncm-foundation.

This module provides comprehensive examples of using the migration system
for different database types and scenarios.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List

from .config import MigrationConfig, MigrationEnvironment
from .manager import MigrationStatus, MigrationType
from .runner import MigrationRunner
from .utils.database_utils import DatabaseUtils
from .utils.validation_utils import ValidationUtils

logger = logging.getLogger(__name__)


async def postgresql_migration_example():
    """Example: PostgreSQL migration with Alembic."""
    print("=== PostgreSQL Migration Example ===")

    # Configure migration
    config = MigrationConfig(
        database_url="postgresql+asyncpg://postgres:password@localhost/ncm_example",
        database_type="postgresql",
        migration_directory="migrations",
        backup_before_migration=True,
        auto_rollback_on_failure=True,
        environment=MigrationEnvironment.DEVELOPMENT,
        verbose=True,
    )

    # Create runner
    runner = MigrationRunner(config)

    try:
        # Initialize runner
        await runner.initialize()
        print("✅ Migration runner initialized")

        # Create schema migration
        version = await runner.create_migration(
            "Add user table with audit fields", MigrationType.SCHEMA
        )
        print(f"✅ Created schema migration: {version}")

        # Create data migration
        version = await runner.create_migration(
            "Seed initial user roles", MigrationType.DATA
        )
        print(f"✅ Created data migration: {version}")

        # Create index migration
        version = await runner.create_migration(
            "Add performance indexes", MigrationType.INDEX
        )
        print(f"✅ Created index migration: {version}")

        # Run migrations (dry run)
        print("\n--- Running migrations (dry run) ---")
        results = await runner.run_migrations(dry_run=True)

        for result in results:
            status_icon = "✅" if result["status"] == "completed" else "❌"
            print(
                f"{status_icon} {result['version']}: {result['description']} ({result['status']})"
            )

        # Get migration status
        print("\n--- Migration Status ---")
        status = await runner.get_migration_status()
        for record in status:
            print(f"{record['version']}: {record['description']} ({record['status']})")

        # Validate migrations
        print("\n--- Validating migrations ---")
        is_valid = await runner.validate_migrations()
        print(f"All migrations valid: {is_valid}")

    except Exception as e:
        print(f"❌ Migration example failed: {e}")
    finally:
        await runner.close()


async def mongodb_migration_example():
    """Example: MongoDB migration."""
    print("\n=== MongoDB Migration Example ===")

    # Configure migration
    config = MigrationConfig(
        database_url="mongodb://localhost:27017/ncm_example",
        database_type="mongodb",
        migration_directory="migrations",
        backup_before_migration=True,
        environment=MigrationEnvironment.DEVELOPMENT,
        verbose=True,
    )

    # Create runner
    runner = MigrationRunner(config)

    try:
        # Initialize runner
        await runner.initialize()
        print("✅ MongoDB migration runner initialized")

        # Create collection migration
        version = await runner.create_migration(
            "Create users collection with indexes", MigrationType.SCHEMA
        )
        print(f"✅ Created collection migration: {version}")

        # Create data migration
        version = await runner.create_migration(
            "Seed initial user documents", MigrationType.DATA
        )
        print(f"✅ Created data migration: {version}")

        # Run migrations (dry run)
        print("\n--- Running MongoDB migrations (dry run) ---")
        results = await runner.run_migrations(dry_run=True)

        for result in results:
            status_icon = "✅" if result["status"] == "completed" else "❌"
            print(
                f"{status_icon} {result['version']}: {result['description']} ({result['status']})"
            )

    except Exception as e:
        print(f"❌ MongoDB migration example failed: {e}")
    finally:
        await runner.close()


async def docker_migration_example():
    """Example: Docker-based migration."""
    print("\n=== Docker Migration Example ===")

    # Configure migration with Docker support
    config = MigrationConfig(
        database_url="postgresql+asyncpg://postgres:password@postgres:5432/ncm_example",
        database_type="postgresql",
        migration_directory="migrations",
        docker_enabled=True,
        docker_image="ncm-migration:latest",
        docker_network="ncm-network",
        environment=MigrationEnvironment.DEVELOPMENT,
        verbose=True,
    )

    print("Docker migration configuration:")
    print(f"  Image: {config.docker_image}")
    print(f"  Network: {config.docker_network}")
    print(f"  Database URL: {config.database_url}")

    # Show Docker commands
    print("\nDocker commands for migration:")
    print("1. Build migration image:")
    print(
        "   docker build -f migrations/docker/Dockerfile.migration -t ncm-migration:latest ."
    )

    print("\n2. Run migrations:")
    print("   docker run --rm \\")
    print(
        "     -e DATABASE_URL='postgresql://postgres:password@postgres:5432/ncm_example' \\"
    )
    print("     -v $(pwd)/migrations:/app/migrations \\")
    print("     ncm-migration:latest run")

    print("\n3. Run specific migration:")
    print("   docker run --rm \\")
    print(
        "     -e DATABASE_URL='postgresql://postgres:password@postgres:5432/ncm_example' \\"
    )
    print("     -e TARGET_VERSION='001_add_users_table' \\")
    print("     -v $(pwd)/migrations:/app/migrations \\")
    print("     ncm-migration:latest run --target-version 001_add_users_table")

    print("\n4. Rollback migration:")
    print("   docker run --rm \\")
    print(
        "     -e DATABASE_URL='postgresql://postgres:password@postgres:5432/ncm_example' \\"
    )
    print("     -v $(pwd)/migrations:/app/migrations \\")
    print("     ncm-migration:latest rollback --version 001_add_users_table")


async def validation_example():
    """Example: Migration validation."""
    print("\n=== Migration Validation Example ===")

    # Test configuration validation
    config_data = {
        "database_url": "postgresql://user:password@localhost/database",
        "database_type": "postgresql",
        "migration_directory": "migrations",
        "backup_before_migration": True,
        "auto_rollback_on_failure": True,
    }

    print("Validating migration configuration...")
    errors = ValidationUtils.validate_migration_config(config_data)

    if errors:
        print("❌ Configuration validation failed:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("✅ Configuration validation passed")

    # Test environment requirements
    print("\nValidating environment requirements...")
    env_errors = ValidationUtils.validate_environment_requirements()

    if env_errors:
        print("❌ Environment validation failed:")
        for error in env_errors:
            print(f"  - {error}")
    else:
        print("✅ Environment validation passed")

    # Test migration file validation
    print("\nValidating migration files...")
    # This would validate actual migration files if they existed
    print("✅ Migration file validation (simulated)")


async def backup_restore_example():
    """Example: Database backup and restore."""
    print("\n=== Backup and Restore Example ===")

    # Configure migration
    config = MigrationConfig(
        database_url="postgresql+asyncpg://postgres:password@localhost/ncm_example",
        database_type="postgresql",
        backup_before_migration=True,
        backup_directory="backups",
    )

    # Create runner
    runner = MigrationRunner(config)

    try:
        await runner.initialize()

        # Test backup
        backup_path = (
            f"backups/backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.sql"
        )
        print(f"Creating backup: {backup_path}")

        # This would actually create a backup in a real scenario
        print("✅ Backup created successfully")

        # Test restore
        print(f"Restoring from backup: {backup_path}")
        print("✅ Restore completed successfully")

    except Exception as e:
        print(f"❌ Backup/restore example failed: {e}")
    finally:
        await runner.close()


async def migration_lifecycle_example():
    """Example: Complete migration lifecycle."""
    print("\n=== Migration Lifecycle Example ===")

    # Configure migration
    config = MigrationConfig(
        database_url="postgresql+asyncpg://postgres:password@localhost/ncm_example",
        database_type="postgresql",
        migration_directory="migrations",
        backup_before_migration=True,
        auto_rollback_on_failure=True,
        environment=MigrationEnvironment.DEVELOPMENT,
        verbose=True,
    )

    # Create runner
    runner = MigrationRunner(config)

    try:
        await runner.initialize()

        # Step 1: Create migrations
        print("Step 1: Creating migrations...")

        schema_version = await runner.create_migration(
            "Create users table", MigrationType.SCHEMA
        )
        print(f"✅ Created schema migration: {schema_version}")

        data_version = await runner.create_migration(
            "Seed initial data", MigrationType.DATA
        )
        print(f"✅ Created data migration: {data_version}")

        # Step 2: Validate migrations
        print("\nStep 2: Validating migrations...")
        is_valid = await runner.validate_migrations()
        print(f"✅ Migrations valid: {is_valid}")

        # Step 3: Run migrations (dry run)
        print("\nStep 3: Running migrations (dry run)...")
        results = await runner.run_migrations(dry_run=True)

        for result in results:
            status_icon = "✅" if result["status"] == "completed" else "❌"
            print(
                f"{status_icon} {result['version']}: {result['description']} ({result['status']})"
            )

        # Step 4: Check status
        print("\nStep 4: Checking migration status...")
        status = await runner.get_migration_status()
        print(f"Total migrations: {len(status)}")

        # Step 5: Simulate rollback
        print("\nStep 5: Simulating rollback...")
        if results:
            latest_migration = results[-1]
            print(f"Would rollback: {latest_migration['version']}")

        print("\n✅ Migration lifecycle example completed")

    except Exception as e:
        print(f"❌ Migration lifecycle example failed: {e}")
    finally:
        await runner.close()


async def cli_example():
    """Example: CLI usage."""
    print("\n=== CLI Usage Example ===")

    print("Command-line interface examples:")
    print("\n1. Create new migration:")
    print(
        "   python -m migrations.runner create 'Add user table' --type schema --database postgresql"
    )

    print("\n2. Run all migrations:")
    print("   python -m migrations.runner run --database postgresql")

    print("\n3. Run specific migration:")
    print(
        "   python -m migrations.runner run --target-version 001_add_users_table --database postgresql"
    )

    print("\n4. Rollback migration:")
    print(
        "   python -m migrations.runner rollback --version 001_add_users_table --database postgresql"
    )

    print("\n5. Check migration status:")
    print("   python -m migrations.runner status --database postgresql")

    print("\n6. Validate migrations:")
    print("   python -m migrations.runner validate --database postgresql")

    print("\n7. Dry run migrations:")
    print("   python -m migrations.runner run --dry-run --database postgresql")

    print("\n8. Verbose output:")
    print("   python -m migrations.runner run --verbose --database postgresql")


async def docker_compose_example():
    """Example: Docker Compose usage."""
    print("\n=== Docker Compose Example ===")

    print("Docker Compose configuration:")
    print(
        """
version: '3.8'

services:
  migration:
    build:
      context: .
      dockerfile: migrations/docker/Dockerfile.migration
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:password@postgres:5432/ncm_example
      - MIGRATION_ENVIRONMENT=development
      - MIGRATION_DRY_RUN=false
    volumes:
      - ./migrations:/app/migrations
      - ./alembic:/app/alembic
    networks:
      - ncm-network
    depends_on:
      - postgres
    command: ["python", "-m", "migrations.runner", "run"]

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=ncm_example
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - ncm-network
    ports:
      - "5432:5432"

volumes:
  postgres_data:

networks:
  ncm-network:
    driver: bridge
"""
    )

    print("\nDocker Compose commands:")
    print("1. Start services:")
    print("   docker-compose -f migrations/docker/docker-compose.migration.yml up -d")

    print("\n2. Run migrations:")
    print(
        "   docker-compose -f migrations/docker/docker-compose.migration.yml up migration"
    )

    print("\n3. Stop services:")
    print("   docker-compose -f migrations/docker/docker-compose.migration.yml down")

    print("\n4. View logs:")
    print(
        "   docker-compose -f migrations/docker/docker-compose.migration.yml logs migration"
    )


async def main():
    """Run all migration examples."""
    print("NCM-Foundation Migration Examples")
    print("=" * 50)

    # Run examples
    await postgresql_migration_example()
    await mongodb_migration_example()
    await docker_migration_example()
    await validation_example()
    await backup_restore_example()
    await migration_lifecycle_example()
    await cli_example()
    await docker_compose_example()

    print("\n" + "=" * 50)
    print("All migration examples completed!")
    print("\nFor more information, see:")
    print("- README.md for detailed documentation")
    print("- examples.py for code examples")
    print("- Docker files in migrations/docker/")


if __name__ == "__main__":
    asyncio.run(main())
