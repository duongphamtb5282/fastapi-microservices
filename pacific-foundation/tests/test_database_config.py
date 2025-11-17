"""Test cases for database configuration."""

import pytest

from ncm_foundation.core.database.config import DatabaseConfig, DatabaseType


class TestDatabaseConfig:
    """Test DatabaseConfig functionality."""

    def test_database_config_creation(self):
        """Test creating DatabaseConfig with default values."""
        config = DatabaseConfig(
            db_type=DatabaseType.POSTGRESQL,
            host="localhost",
            database="test_db"
        )

        assert config.db_type == DatabaseType.POSTGRESQL
        assert config.host == "localhost"
        assert config.port == 5432  # Default port
        assert config.database == "test_db"
        assert config.username == "postgres"  # Default username
        assert config.pool_size == 10  # Default pool size

    def test_database_type_enum(self):
        """Test DatabaseType enum values."""
        assert DatabaseType.POSTGRESQL.value == "postgresql"
        assert DatabaseType.MYSQL.value == "mysql"
        assert DatabaseType.SQLITE.value == "sqlite"
        assert DatabaseType.MONGODB.value == "mongodb"
        assert DatabaseType.NEO4J.value == "neo4j"

    def test_database_config_validation(self):
        """Test DatabaseConfig validation."""
        # Valid configuration
        config = DatabaseConfig(
            db_type=DatabaseType.POSTGRESQL,
            host="localhost",
            port=5432,
            database="test",
            username="user",
            password="pass"
        )
        assert config.host == "localhost"

    def test_database_config_with_custom_values(self):
        """Test DatabaseConfig with custom values."""
        config = DatabaseConfig(
            db_type=DatabaseType.MYSQL,
            host="mysql.example.com",
            port=3306,
            database="myapp",
            username="myuser",
            password="mypass",
            pool_size=20,
            max_overflow=30
        )

        assert config.db_type == DatabaseType.MYSQL
        assert config.host == "mysql.example.com"
        assert config.port == 3306
        assert config.database == "myapp"
        assert config.username == "myuser"
        assert config.password == "mypass"
        assert config.pool_size == 20
        assert config.max_overflow == 30
