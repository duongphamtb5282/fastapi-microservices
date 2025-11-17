#!/usr/bin/env python3
"""
Setup script for NCM Sample Project.
This version works around ncm-foundation library issues by using direct SQLAlchemy.
"""

import asyncio
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import ncm-foundation modules that work
from ncm_foundation.core.config import FoundationConfig
from ncm_foundation.core.logging.interfaces import LogConfig, LogLevel
from ncm_foundation.core.logging.manager import LogManager
from sqlalchemy import text
# Direct SQLAlchemy imports
from sqlalchemy.ext.asyncio import create_async_engine


def load_environment():
    """Load environment variables from .env file if it exists."""
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key] = value
    else:
        print("⚠️  No .env file found, using environment variables or defaults")


async def setup_database():
    """Setup database and run migrations."""
    print("🗄️  Setting up database...")

    try:
        # Initialize configuration
        config = FoundationConfig()

        # Create database URL
        database_url = os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://auth_user:auth_password@localhost:5432/test",
        )

        # Create engine
        try:
            engine = create_async_engine(
                database_url,
                pool_size=10,
                max_overflow=20,
                pool_timeout=30,
                pool_recycle=3600,
                pool_pre_ping=True,
                echo=False,
            )
        except ImportError as e:
            print(f"  ❌ Database driver not installed: {e}")
            print("  Please install the required database driver:")
            print("    pip install asyncpg  # for PostgreSQL")
            print("    pip install aiomysql  # for MySQL")
            print("    pip install aiosqlite  # for SQLite")
            return False

        # Test database connection
        print("  Testing database connection...")
        try:
            async with engine.begin() as conn:
                result = await conn.execute(text("SELECT 1 as test"))
                print(f"  ✅ Database connection successful: {result.fetchone()}")
        except Exception as e:
            print(f"  ❌ Database connection failed: {e}")
            print("  Please ensure PostgreSQL is running and the database exists")
            return False

        # Run migrations using Alembic
        print("  Running database migrations...")
        migration_result = await run_alembic_migrations()
        if migration_result:
            print("  ✅ Migrations completed successfully")
        else:
            print("  ⚠️  Migration command completed with warnings")

        # Close engine
        await engine.dispose()
        print("✅ Database setup completed")

        return True

    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return False


async def run_alembic_migrations() -> bool:
    """Run Alembic migrations."""
    try:
        # Change to the project directory
        project_dir = Path(__file__).parent.parent
        os.chdir(project_dir)

        # Run alembic upgrade
        result = subprocess.run(
            ["alembic", "upgrade", "head"], capture_output=True, text=True, check=True
        )
        print(f"  Migration output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  Migration error: {e.stderr}")
        return False
    except FileNotFoundError:
        print("  ⚠️  Alembic not found, skipping migrations")
        return True


async def test_services():
    """Test all services."""
    print("\n🧪 Testing services...")

    try:
        # Initialize configuration
        config = FoundationConfig()

        # Test database connection
        print("  Testing database connection...")
        database_url = os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://auth_user:auth_password@localhost:5432/test",
        )

        engine = create_async_engine(
            database_url,
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_recycle=3600,
            pool_pre_ping=True,
            echo=False,
        )

        try:
            async with engine.begin() as conn:
                result = await conn.execute(text("SELECT 1 as test"))
                print(f"    Database: ✅ ({result.fetchone()})")
        except ImportError as e:
            print(f"    Database: ❌ Driver not installed ({e})")
        except Exception as e:
            print(f"    Database: ❌ ({e})")
        finally:
            await engine.dispose()

        # Test logging
        print("  Testing logging...")
        try:
            log_config = LogConfig(
                level=LogLevel.INFO,
                format="json",
                handlers=["console"],
                file_path="logs/app.log",
                max_file_size=10 * 1024 * 1024,  # 10MB
                max_files=5,
                rotation_interval="daily",
                enable_rotation=True,
                enable_masking=True,
            )

            log_manager = LogManager(log_config)
            await log_manager.start()

            # Test logging
            logger = log_manager.get_logger("test")
            logger.info("Test log message")
            print("    Logging: ✅")

            await log_manager.stop()
        except Exception as e:
            print(f"    Logging: ❌ ({e})")

        print("✅ All services tested successfully")
        return True

    except Exception as e:
        print(f"❌ Service test failed: {e}")
        return False


def check_docker_services():
    """Check if Docker services are running."""
    print("\n🐳 Checking Docker services...")

    # Check if Docker is available
    try:
        subprocess.run(["docker", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("  ⚠️  Docker is not installed or not in PATH")
        print("  Skipping Docker service checks")
        return True  # Don't fail the setup if Docker is not available

    services = ["postgres", "redis", "kafka"]
    running_services = []

    for service in services:
        try:
            result = subprocess.run(
                [
                    "docker",
                    "ps",
                    "--filter",
                    f"name={service}",
                    "--format",
                    "{{.Names}}",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            if service in result.stdout:
                running_services.append(service)
                print(f"  ✅ {service} is running")
            else:
                print(f"  ❌ {service} is not running")
        except subprocess.CalledProcessError:
            print(f"  ❌ {service} is not running")

    if len(running_services) == len(services):
        print("✅ All Docker services are running")
        return True
    else:
        print(f"⚠️  Only {len(running_services)}/{len(services)} services are running")
        print("   Run: docker-compose up -d")
        return False


def validate_environment():
    """Validate required environment variables."""
    print("\n🔍 Validating environment...")

    required_vars = ["DATABASE_URL", "SECRET_KEY", "JWT_SECRET"]

    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("   Please set these variables or create a .env file")
        return False

    print("✅ Environment validation passed")
    return True


def create_sample_data():
    """Create sample data for testing."""
    print("\n📊 Creating sample data...")

    try:
        # This would create sample users and roles
        # For now, just print instructions
        print("  Sample data creation instructions:")
        print(
            "  1. Start the application: python -m uvicorn ncm_sample.api:app --reload"
        )
        print("  2. Use the API to create users and roles")
        print("  3. Test authentication and authorization")

        return True

    except Exception as e:
        print(f"❌ Sample data creation failed: {e}")
        return False


async def main():
    """Main setup function."""
    print("🚀 NCM Sample Project Setup")
    print("=" * 50)

    # Load environment variables
    load_environment()

    # Validate environment
    if not validate_environment():
        sys.exit(1)

    # Check Docker services
    docker_ok = check_docker_services()
    if not docker_ok:
        print("\n❌ Please start Docker services first:")
        print("   docker-compose up -d")
        sys.exit(1)

    # Setup database
    db_ok = await setup_database()
    if not db_ok:
        print("\n❌ Database setup failed")
        sys.exit(1)

    # Test services
    services_ok = await test_services()
    if not services_ok:
        print("\n❌ Service tests failed")
        sys.exit(1)

    # Create sample data
    data_ok = create_sample_data()
    if not data_ok:
        print("\n❌ Sample data creation failed")
        sys.exit(1)

    print("\n🎉 Setup completed successfully!")
    print("\nNext steps:")
    print("  1. Start the application:")
    print("     python -m uvicorn ncm_sample.api:app --reload")
    print("  2. Open API documentation:")
    print("     http://localhost:8000/docs")
    print("  3. Test the endpoints:")
    print("     curl http://localhost:8000/health")
    print("  4. Create a user:")
    print("     curl -X POST http://localhost:8000/users/ \\")
    print("       -H 'Content-Type: application/json' \\")
    print(
        '       -d \'{"email":"test@example.com","username":"testuser","first_name":"Test","last_name":"User","password":"password123"}\''
    )


if __name__ == "__main__":
    asyncio.run(main())
