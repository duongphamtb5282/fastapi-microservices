#!/usr/bin/env python3
"""Database migration commands."""

import asyncio
import click
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Load environment file
try:
    from dotenv import load_dotenv
    env_file = f".env.{os.getenv('ENVIRONMENT', 'dev')}"
    env_path = Path(__file__).parent.parent / env_file
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Loaded environment file: {env_path}")
    else:
        print(f"⚠️  Environment file not found: {env_path}")
except ImportError:
    print("⚠️  python-dotenv not available, skipping .env file loading")

from alembic.config import Config
from alembic import command
from ncm_foundation.core.database import DatabaseManager
from ncm_foundation.core.config import FoundationConfig
from ncm_sample.config.settings import get_settings

@click.group()
def cli():
    """Database migration commands."""
    pass

@cli.command()
@click.option('--env', default='dev', help='Environment (dev/prod)')
def upgrade(env: str):
    """Run database migrations."""
    os.environ['ENVIRONMENT'] = env

    try:
        # Load settings to get the correct database URL
        settings = get_settings()

        # Run alembic upgrade with the correct database URL
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)
        command.upgrade(alembic_cfg, "head")
        print(f"✅ Database upgraded for {env} environment")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)

@cli.command()
@click.option('--env', default='dev', help='Environment (dev/prod)')
@click.option('--revision', required=True, help='Revision to downgrade to')
def downgrade(env: str, revision: str):
    """Downgrade database to specific revision."""
    os.environ['ENVIRONMENT'] = env
    
    try:
        # Run alembic downgrade
        alembic_cfg = Config("alembic.ini")
        command.downgrade(alembic_cfg, revision)
        print(f"✅ Database downgraded to {revision} for {env} environment")
    except Exception as e:
        print(f"❌ Downgrade failed: {e}")
        sys.exit(1)

@cli.command()
@click.option('--env', default='dev', help='Environment (dev/prod)')
def current(env: str):
    """Show current database revision."""
    os.environ['ENVIRONMENT'] = env
    
    try:
        alembic_cfg = Config("alembic.ini")
        command.current(alembic_cfg)
    except Exception as e:
        print(f"❌ Failed to get current revision: {e}")
        sys.exit(1)

@cli.command()
@click.option('--message', required=True, help='Migration message')
def create(message: str):
    """Create a new migration."""
    try:
        alembic_cfg = Config("alembic.ini")
        command.revision(alembic_cfg, autogenerate=True, message=message)
        print(f"✅ Migration created: {message}")
    except Exception as e:
        print(f"❌ Failed to create migration: {e}")
        sys.exit(1)

@cli.command()
@click.option('--env', default='dev', help='Environment (dev/prod)')
def history(env: str):
    """Show migration history."""
    os.environ['ENVIRONMENT'] = env
    
    try:
        alembic_cfg = Config("alembic.ini")
        command.history(alembic_cfg)
    except Exception as e:
        print(f"❌ Failed to get migration history: {e}")
        sys.exit(1)

if __name__ == "__main__":
    cli()