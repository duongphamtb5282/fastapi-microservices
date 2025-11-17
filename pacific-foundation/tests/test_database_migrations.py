"""Test cases for database migrations."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ncm_foundation.core.database.config import DatabaseConfig, DatabaseType
from ncm_foundation.core.database.manager import DatabaseManager
from ncm_foundation.core.database.migrations.manager import AlembicMigrationManager


class TestMigrationManager:
    """Test migration manager functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = DatabaseConfig(
            db_type=DatabaseType.POSTGRESQL,
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password="test_pass"
        )

    def test_migration_manager_initialization(self):
        """Test migration manager can be initialized."""
        with patch('ncm_foundation.core.database.providers.sqlalchemy_provider.create_async_engine') as mock_engine:
            mock_engine.return_value = MagicMock()
            mock_provider = MagicMock()
            mock_provider.connect = AsyncMock()

            with patch('ncm_foundation.core.database.manager.DatabaseFactory.create_provider', return_value=mock_provider):
                db_manager = DatabaseManager(self.config)
                migration_manager = db_manager.migration_manager

                assert migration_manager is not None
                assert isinstance(migration_manager, AlembicMigrationManager)

    @pytest.mark.asyncio
    async def test_migration_run(self):
        """Test running migrations."""
        with patch('ncm_foundation.core.database.providers.sqlalchemy_provider.create_async_engine') as mock_engine:
            mock_engine.return_value = MagicMock()
            mock_provider = MagicMock()
            mock_provider.connect = AsyncMock()

            with patch('ncm_foundation.core.database.manager.DatabaseFactory.create_provider', return_value=mock_provider):
                db_manager = DatabaseManager(self.config)

                # Mock the migration manager
                migration_manager = MagicMock()
                migration_manager.run_migrations = AsyncMock(return_value=[])
                db_manager.migration_manager = migration_manager

                result = await db_manager.run_migrations()
                assert result == []

    @pytest.mark.asyncio
    async def test_migration_status(self):
        """Test getting migration status."""
        with patch('ncm_foundation.core.database.providers.sqlalchemy_provider.create_async_engine') as mock_engine:
            mock_engine.return_value = MagicMock()
            mock_provider = MagicMock()
            mock_provider.connect = AsyncMock()

            with patch('ncm_foundation.core.database.manager.DatabaseFactory.create_provider', return_value=mock_provider):
                db_manager = DatabaseManager(self.config)

                # Mock the migration manager
                migration_manager = MagicMock()
                migration_manager.get_migration_status = AsyncMock(return_value=[])
                db_manager.migration_manager = migration_manager

                result = await db_manager.get_migration_status()
                assert result == []

    def test_migration_creation(self):
        """Test creating new migrations."""
        with patch('ncm_foundation.core.database.providers.sqlalchemy_provider.create_async_engine') as mock_engine:
            mock_engine.return_value = MagicMock()
            mock_provider = MagicMock()
            mock_provider.connect = AsyncMock()

            with patch('ncm_foundation.core.database.manager.DatabaseFactory.create_provider', return_value=mock_provider):
                db_manager = DatabaseManager(self.config)

                # Mock the migration manager
                migration_manager = MagicMock()
                migration_manager.create_migration = AsyncMock(return_value="test_migration_id")
                db_manager.migration_manager = migration_manager

                result = await db_manager.create_migration("test_migration", "Test migration")
                assert result == "test_migration_id"
