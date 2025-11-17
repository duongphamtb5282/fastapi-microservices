"""
Migration utility functions.
"""

import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MigrationUtils:
    """Migration utility functions."""

    @staticmethod
    def create_migration_directory(base_path: str) -> Path:
        """Create migration directory structure."""
        migration_path = Path(base_path) / "migrations"
        migration_path.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (migration_path / "versions").mkdir(exist_ok=True)
        (migration_path / "templates").mkdir(exist_ok=True)
        (migration_path / "scripts").mkdir(exist_ok=True)
        (migration_path / "backups").mkdir(exist_ok=True)

        # Create __init__.py files
        for subdir in ["versions", "templates", "scripts", "backups"]:
            init_file = migration_path / subdir / "__init__.py"
            if not init_file.exists():
                init_file.write_text("")

        logger.info(f"Created migration directory structure: {migration_path}")
        return migration_path

    @staticmethod
    def generate_migration_filename(
        description: str, migration_type: str = "schema"
    ) -> str:
        """Generate migration filename."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_description = "".join(
            c if c.isalnum() or c in ("-", "_") else "_" for c in description.lower()
        )
        return f"{timestamp}_{migration_type}_{safe_description}.py"

    @staticmethod
    def copy_migration_template(
        template_path: str, output_path: str, variables: Dict[str, Any]
    ) -> None:
        """Copy and customize migration template."""
        try:
            with open(template_path, "r") as template_file:
                content = template_file.read()

            # Replace variables
            for key, value in variables.items():
                content = content.replace(f"${{{key}}}", str(value))

            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            with open(output_path, "w") as output_file:
                output_file.write(content)

            logger.info(f"Created migration file: {output_path}")

        except Exception as e:
            logger.error(f"Failed to copy migration template: {e}")
            raise

    @staticmethod
    def cleanup_failed_migration(migration_path: str) -> None:
        """Cleanup failed migration files."""
        try:
            if os.path.exists(migration_path):
                if os.path.isdir(migration_path):
                    shutil.rmtree(migration_path)
                else:
                    os.remove(migration_path)
                logger.info(f"Cleaned up failed migration: {migration_path}")
        except Exception as e:
            logger.error(f"Failed to cleanup migration: {e}")

    @staticmethod
    def validate_migration_file(file_path: str) -> List[str]:
        """Validate migration file syntax."""
        errors = []

        try:
            with open(file_path, "r") as f:
                content = f.read()

            # Check for required functions
            required_functions = ["upgrade", "downgrade"]
            for func in required_functions:
                if f"def {func}(" not in content:
                    errors.append(f"Missing required function: {func}")

            # Check for syntax errors
            try:
                compile(content, file_path, "exec")
            except SyntaxError as e:
                errors.append(f"Syntax error: {e}")

            # Check for common issues
            if "import" not in content:
                errors.append("Missing import statements")

            if "alembic" not in content and "op." not in content:
                errors.append("Missing Alembic operations")

        except Exception as e:
            errors.append(f"Failed to read file: {e}")

        return errors

    @staticmethod
    def get_migration_dependencies(file_path: str) -> List[str]:
        """Extract migration dependencies from file."""
        dependencies = []

        try:
            with open(file_path, "r") as f:
                content = f.read()

            # Look for dependency comments
            lines = content.split("\n")
            for line in lines:
                if line.strip().startswith("# DEPENDS_ON:"):
                    dep = line.split(":", 1)[1].strip()
                    dependencies.append(dep)

        except Exception as e:
            logger.error(f"Failed to extract dependencies: {e}")

        return dependencies

    @staticmethod
    def create_migration_metadata(
        version: str,
        description: str,
        migration_type: str,
        dependencies: List[str] = None,
        author: str = None,
        tags: List[str] = None,
    ) -> Dict[str, Any]:
        """Create migration metadata."""
        return {
            "version": version,
            "description": description,
            "migration_type": migration_type,
            "created_at": datetime.utcnow().isoformat(),
            "dependencies": dependencies or [],
            "author": author or "system",
            "tags": tags or [],
            "status": "pending",
        }

    @staticmethod
    def save_migration_metadata(file_path: str, metadata: Dict[str, Any]) -> None:
        """Save migration metadata to file."""
        try:
            metadata_path = file_path.replace(".py", ".meta.json")
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")

    @staticmethod
    def load_migration_metadata(file_path: str) -> Optional[Dict[str, Any]]:
        """Load migration metadata from file."""
        try:
            metadata_path = file_path.replace(".py", ".meta.json")
            if os.path.exists(metadata_path):
                with open(metadata_path, "r") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load metadata: {e}")
        return None

    @staticmethod
    def generate_migration_summary(migration_dir: str) -> Dict[str, Any]:
        """Generate migration summary."""
        try:
            migration_path = Path(migration_dir)
            if not migration_path.exists():
                return {"error": "Migration directory does not exist"}

            migrations = []
            for file_path in migration_path.glob("*.py"):
                if file_path.name != "__init__.py":
                    metadata = MigrationUtils.load_migration_metadata(str(file_path))
                    if metadata:
                        migrations.append(metadata)

            # Sort by version
            migrations.sort(key=lambda x: x.get("version", ""))

            return {
                "total_migrations": len(migrations),
                "migrations": migrations,
                "generated_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to generate migration summary: {e}")
            return {"error": str(e)}

    @staticmethod
    def create_alembic_config(
        database_url: str,
        script_location: str = "alembic",
        output_path: str = "alembic.ini",
    ) -> None:
        """Create Alembic configuration file."""
        config_content = f"""[alembic]
script_location = {script_location}
prepend_sys_path = .
version_path_separator = os
sqlalchemy.url = {database_url}

[post_write_hooks]
hooks = black
black.type = console_scripts
black.entrypoint = black
black.options = -l 88 REVISION_SCRIPT_FILENAME

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
"""

        try:
            with open(output_path, "w") as f:
                f.write(config_content)
            logger.info(f"Created Alembic config: {output_path}")
        except Exception as e:
            logger.error(f"Failed to create Alembic config: {e}")
            raise

    @staticmethod
    def create_alembic_env(
        script_location: str = "alembic", output_path: str = "alembic/env.py"
    ) -> None:
        """Create Alembic environment file."""
        env_content = '''"""Alembic environment configuration."""

import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
from alembic.runtime.migration import MigrationContext

# Import your models here
# from your_app.models import Base

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the target metadata
# target_metadata = Base.metadata
target_metadata = None

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection: Connection) -> None:
    """Run migrations with connection."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations() -> None:
    """Run migrations in async mode."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
'''

        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            with open(output_path, "w") as f:
                f.write(env_content)
            logger.info(f"Created Alembic env: {output_path}")
        except Exception as e:
            logger.error(f"Failed to create Alembic env: {e}")
            raise

    @staticmethod
    def create_migration_script_template(
        script_location: str = "alembic", output_path: str = "alembic/script.py.mako"
    ) -> None:
        """Create Alembic script template."""
        template_content = '''"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}

def upgrade() -> None:
    """Upgrade database schema."""
    ${upgrades if upgrades else "pass"}

def downgrade() -> None:
    """Downgrade database schema."""
    ${downgrades if downgrades else "pass"}
'''

        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            with open(output_path, "w") as f:
                f.write(template_content)
            logger.info(f"Created Alembic script template: {output_path}")
        except Exception as e:
            logger.error(f"Failed to create Alembic script template: {e}")
            raise
