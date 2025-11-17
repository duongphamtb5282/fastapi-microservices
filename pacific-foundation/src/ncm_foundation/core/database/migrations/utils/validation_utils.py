"""
Migration validation utilities.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ValidationUtils:
    """Migration validation utilities."""

    @staticmethod
    def validate_migration_config(config: Dict[str, Any]) -> List[str]:
        """Validate migration configuration."""
        errors = []

        # Required fields
        required_fields = ["database_url", "database_type"]
        for field in required_fields:
            if field not in config or not config[field]:
                errors.append(f"Missing required field: {field}")

        # Validate database type
        valid_types = ["postgresql", "mysql", "sqlite", "mongodb"]
        if "database_type" in config and config["database_type"] not in valid_types:
            errors.append(f"Invalid database type: {config['database_type']}")

        # Validate database URL format
        if "database_url" in config:
            db_url = config["database_url"]
            if not db_url.startswith(
                ("postgresql://", "mysql://", "sqlite://", "mongodb://")
            ):
                errors.append("Invalid database URL format")

        # Validate numeric fields
        numeric_fields = ["pool_size", "max_overflow", "timeout", "retry_attempts"]
        for field in numeric_fields:
            if field in config and not isinstance(config[field], (int, float)):
                errors.append(f"Invalid {field}: must be numeric")

        # Validate boolean fields
        boolean_fields = ["dry_run", "verbose", "backup_before_migration"]
        for field in boolean_fields:
            if field in config and not isinstance(config[field], bool):
                errors.append(f"Invalid {field}: must be boolean")

        return errors

    @staticmethod
    def validate_migration_file(file_path: str) -> List[str]:
        """Validate migration file."""
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

            # Check for dangerous operations
            dangerous_operations = ["DROP TABLE", "DELETE FROM", "TRUNCATE"]
            for operation in dangerous_operations:
                if operation in content.upper():
                    errors.append(f"Potentially dangerous operation: {operation}")

        except Exception as e:
            errors.append(f"Failed to read file: {e}")

        return errors

    @staticmethod
    def validate_migration_dependencies(migrations: List[Dict[str, Any]]) -> List[str]:
        """Validate migration dependencies."""
        errors = []

        # Create dependency graph
        dependency_graph = {}
        for migration in migrations:
            version = migration.get("version")
            dependencies = migration.get("dependencies", [])
            dependency_graph[version] = dependencies

        # Check for circular dependencies
        for version in dependency_graph:
            if ValidationUtils._has_circular_dependency(
                version, dependency_graph, set()
            ):
                errors.append(f"Circular dependency detected for migration: {version}")

        # Check for missing dependencies
        all_versions = set(dependency_graph.keys())
        for version, dependencies in dependency_graph.items():
            for dep in dependencies:
                if dep not in all_versions:
                    errors.append(f"Missing dependency {dep} for migration {version}")

        return errors

    @staticmethod
    def _has_circular_dependency(
        version: str, graph: Dict[str, List[str]], visited: set
    ) -> bool:
        """Check for circular dependencies."""
        if version in visited:
            return True

        visited.add(version)
        for dep in graph.get(version, []):
            if ValidationUtils._has_circular_dependency(dep, graph, visited.copy()):
                return True

        return False

    @staticmethod
    def validate_database_connection(provider) -> List[str]:
        """Validate database connection."""
        errors = []

        try:
            # This would need to be implemented based on provider type
            # For now, just return empty list
            pass
        except Exception as e:
            errors.append(f"Database connection validation failed: {e}")

        return errors

    @staticmethod
    def validate_migration_metadata(metadata: Dict[str, Any]) -> List[str]:
        """Validate migration metadata."""
        errors = []

        # Required fields
        required_fields = ["version", "description", "migration_type"]
        for field in required_fields:
            if field not in metadata or not metadata[field]:
                errors.append(f"Missing required metadata field: {field}")

        # Validate version format
        if "version" in metadata:
            version = metadata["version"]
            if not isinstance(version, str) or not version:
                errors.append("Invalid version format")

        # Validate migration type
        valid_types = ["schema", "data", "index", "seed", "custom"]
        if "migration_type" in metadata:
            if metadata["migration_type"] not in valid_types:
                errors.append(f"Invalid migration type: {metadata['migration_type']}")

        # Validate dependencies
        if "dependencies" in metadata:
            deps = metadata["dependencies"]
            if not isinstance(deps, list):
                errors.append("Dependencies must be a list")
            else:
                for dep in deps:
                    if not isinstance(dep, str):
                        errors.append("Dependency must be a string")

        return errors

    @staticmethod
    def validate_backup_requirements(config: Dict[str, Any]) -> List[str]:
        """Validate backup requirements."""
        errors = []

        if config.get("backup_before_migration", False):
            # Check if backup directory is writable
            backup_dir = config.get("backup_directory", "backups")
            try:
                import os

                if not os.path.exists(backup_dir):
                    os.makedirs(backup_dir, exist_ok=True)

                # Test write permissions
                test_file = os.path.join(backup_dir, "test_write.tmp")
                with open(test_file, "w") as f:
                    f.write("test")
                os.remove(test_file)

            except Exception as e:
                errors.append(f"Backup directory not writable: {e}")

        return errors

    @staticmethod
    def validate_environment_requirements() -> List[str]:
        """Validate environment requirements."""
        errors = []

        # Check Python version
        import sys

        if sys.version_info < (3, 8):
            errors.append("Python 3.8 or higher required")

        # Check required packages
        required_packages = [
            "sqlalchemy",
            "alembic",
            "pydantic",
            "motor",  # For MongoDB
            "asyncpg",  # For PostgreSQL
            "aiomysql",  # For MySQL
        ]

        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                errors.append(f"Required package not installed: {package}")

        return errors

    @staticmethod
    def validate_migration_sequence(migrations: List[Dict[str, Any]]) -> List[str]:
        """Validate migration sequence."""
        errors = []

        # Sort migrations by version
        sorted_migrations = sorted(migrations, key=lambda x: x.get("version", ""))

        # Check for duplicate versions
        versions = [m.get("version") for m in sorted_migrations]
        if len(versions) != len(set(versions)):
            errors.append("Duplicate migration versions found")

        # Check for gaps in sequence
        for i in range(1, len(sorted_migrations)):
            prev_version = sorted_migrations[i - 1].get("version", "")
            curr_version = sorted_migrations[i].get("version", "")

            # This is a simplified check - in practice, you'd want more sophisticated version comparison
            if prev_version >= curr_version:
                errors.append(
                    f"Migration sequence error: {prev_version} >= {curr_version}"
                )

        return errors

    @staticmethod
    def generate_validation_report(validation_results: Dict[str, List[str]]) -> str:
        """Generate validation report."""
        report = []
        report.append("Migration Validation Report")
        report.append("=" * 50)
        report.append(f"Generated at: {datetime.utcnow().isoformat()}")
        report.append("")

        total_errors = 0
        for category, errors in validation_results.items():
            report.append(f"{category.upper()}:")
            if errors:
                for error in errors:
                    report.append(f"  ❌ {error}")
                total_errors += len(errors)
            else:
                report.append("  ✅ No errors")
            report.append("")

        report.append(f"Total errors: {total_errors}")

        if total_errors == 0:
            report.append("✅ All validations passed!")
        else:
            report.append("❌ Validation failed!")

        return "\n".join(report)
