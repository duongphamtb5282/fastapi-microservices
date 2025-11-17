"""Alembic migration environment."""

import asyncio
import os
import sys
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import your models
from ncm_sample.features.user_management.models.user import User

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = User.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def get_url():
    """Get database URL from environment or config."""
    return os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url"))

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    print("🔧 Creating async engine for migration...")

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    print("🔗 Connecting to database...")
    async with connectable.connect() as connection:
        print("✅ Connected to database, running migrations...")
        await connection.run_sync(do_run_migrations)
        print("✅ Migrations executed")

    print("🧹 Disposing engine...")
    await connectable.dispose()
    print("✅ Migration process completed")


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    print("🔄 Running migrations in ONLINE mode")
    print(f"📊 Database URL: {get_url()}")

    try:
        # Try to get the current event loop
        try:
            loop = asyncio.get_running_loop()
            print("⚠️  Event loop already running, using threading approach")
            # If we're in an existing loop, run the migration in a separate thread
            import threading

            result = {'success': False, 'error': None}

            def run_migration():
                try:
                    asyncio.run(run_async_migrations())
                    result['success'] = True
                except Exception as e:
                    result['error'] = e

            thread = threading.Thread(target=run_migration, daemon=True)
            thread.start()
            thread.join(timeout=30)  # Wait up to 30 seconds

            if result['success']:
                print("✅ Migration completed successfully in thread")
            else:
                raise result['error'] or Exception("Migration failed in thread")

        except RuntimeError:
            print("🚀 No event loop running, using asyncio.run")
            # No event loop running, we can use asyncio.run safely
            asyncio.run(run_async_migrations())
            print("✅ Migration completed successfully")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()