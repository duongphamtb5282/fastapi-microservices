#!/usr/bin/env python3
"""
Development script for NCM Foundation Library.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ncm_foundation import CacheManager, DatabaseManager, FoundationConfig, LogManager


async def setup_development_environment():
    """Setup development environment."""
    print("🚀 Setting up NCM Foundation development environment...")

    # Set default environment variables
    env_vars = {
        "DATABASE_URL": "postgresql://postgres:password@localhost:5432/ncm_dev",
        "REDIS_URL": "redis://localhost:6379",
        "SECRET_KEY": "dev-secret-key-change-in-production",
        "JWT_SECRET": "dev-jwt-secret-change-in-production",
        "LOG_LEVEL": "DEBUG",
        "LOG_FORMAT": "json",
    }

    for key, value in env_vars.items():
        if key not in os.environ:
            os.environ[key] = value
            print(f"  Set {key}={value}")

    print("✅ Environment variables configured")


async def test_services():
    """Test all foundation services."""
    print("\n🧪 Testing foundation services...")

    try:
        # Initialize configuration
        config = FoundationConfig.from_env()

        # Initialize managers
        db_manager = DatabaseManager(config.database)
        cache_manager = CacheManager(config.cache)
        log_manager = LogManager(config.logging)

        # Start services
        print("  Starting database manager...")
        await db_manager.start()

        print("  Starting cache manager...")
        await cache_manager.start()

        print("  Starting log manager...")
        await log_manager.start()

        # Test health checks
        print("  Testing health checks...")
        db_health = await db_manager.health_check()
        cache_health = await cache_manager.health_check()

        print(f"    Database: {'✅' if db_health else '❌'}")
        print(f"    Cache: {'✅' if cache_health else '❌'}")

        # Get statistics
        print("  Getting service statistics...")
        db_stats = db_manager.get_stats()
        cache_stats = cache_manager.get_stats()
        log_stats = log_manager.get_stats()

        print(f"    Database stats: {len(db_stats)} items")
        print(f"    Cache stats: {len(cache_stats)} items")
        print(f"    Log stats: {len(log_stats)} items")

        print("✅ All services tested successfully")

        return True

    except Exception as e:
        print(f"❌ Service test failed: {e}")
        return False

    finally:
        # Cleanup
        try:
            if "cache_manager" in locals():
                await cache_manager.stop()
            if "db_manager" in locals():
                await db_manager.stop()
            if "log_manager" in locals():
                await log_manager.stop()
        except Exception as e:
            print(f"⚠️  Cleanup warning: {e}")


async def run_migrations():
    """Run database migrations."""
    print("\n🗄️  Running database migrations...")

    try:
        config = FoundationConfig.from_env()
        db_manager = DatabaseManager(config.database)

        await db_manager.start()

        # Run migrations
        migrations = await db_manager.run_migrations()
        print(f"  Applied {len(migrations)} migrations")

        # Get migration status
        status = await db_manager.get_migration_status()
        print(f"  Migration status: {len(status)} migrations tracked")

        print("✅ Migrations completed")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

    finally:
        if "db_manager" in locals():
            await db_manager.stop()

    return True


async def main():
    """Main development script."""
    print("🔧 NCM Foundation Development Script")
    print("=" * 50)

    # Setup environment
    await setup_development_environment()

    # Test services
    services_ok = await test_services()

    if not services_ok:
        print("\n❌ Service tests failed. Please check your configuration.")
        sys.exit(1)

    # Run migrations
    migrations_ok = await run_migrations()

    if not migrations_ok:
        print("\n❌ Migrations failed. Please check your database connection.")
        sys.exit(1)

    print("\n🎉 Development environment is ready!")
    print("\nNext steps:")
    print("  1. Run tests: poetry run pytest")
    print("  2. Start development server: poetry run python examples/basic_usage.py")
    print("  3. Check documentation: docs/")
    print("  4. Run linting: poetry run ruff check src/")


if __name__ == "__main__":
    asyncio.run(main())
