"""Test cases for database manager."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ncm_foundation.core.database.config import DatabaseConfig, DatabaseType
from ncm_foundation.core.database.manager import DatabaseManager
from ncm_foundation.core.database.providers.sqlalchemy_provider import SQLAlchemyProvider


class TestDatabaseManager:
    """Test DatabaseManager functionality."""

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

    @pytest.mark.asyncio
    async def test_database_manager_initialization(self):
        """Test DatabaseManager can be initialized."""
        with patch('ncm_foundation.core.database.providers.sqlalchemy_provider.create_async_engine') as mock_engine:
            mock_engine.return_value = MagicMock()
            mock_provider = MagicMock(spec=SQLAlchemyProvider)
            mock_provider.connect = AsyncMock()

            with patch('ncm_foundation.core.database.manager.DatabaseFactory.create_provider', return_value=mock_provider):
                db_manager = DatabaseManager(self.config)

                assert db_manager.config == self.config
                assert db_manager.provider == mock_provider
                assert db_manager.enable_pooling is True
                assert db_manager.enable_audit is True

    @pytest.mark.asyncio
    async def test_database_manager_connection(self):
        """Test database connection functionality."""
        with patch('ncm_foundation.core.database.providers.sqlalchemy_provider.create_async_engine') as mock_engine:
            mock_engine.return_value = MagicMock()
            mock_provider = MagicMock(spec=SQLAlchemyProvider)
            mock_provider.connect = AsyncMock()
            mock_provider.disconnect = AsyncMock()
            mock_provider.health_check = AsyncMock(return_value=True)

            with patch('ncm_foundation.core.database.manager.DatabaseFactory.create_provider', return_value=mock_provider):
                db_manager = DatabaseManager(self.config)

                await db_manager.connect()
                mock_provider.connect.assert_called_once()

                await db_manager.disconnect()
                mock_provider.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check functionality."""
        with patch('ncm_foundation.core.database.providers.sqlalchemy_provider.create_async_engine') as mock_engine:
            mock_engine.return_value = MagicMock()
            mock_provider = MagicMock(spec=SQLAlchemyProvider)
            mock_provider.health_check = AsyncMock(return_value=True)

            with patch('ncm_foundation.core.database.manager.DatabaseFactory.create_provider', return_value=mock_provider):
                db_manager = DatabaseManager(self.config)

                health = await db_manager.health_check()
                assert health is True

    def test_transaction_manager_initialization(self):
        """Test transaction manager is properly initialized."""
        with patch('ncm_foundation.core.database.providers.sqlalchemy_provider.create_async_engine') as mock_engine:
            mock_engine.return_value = MagicMock()
            mock_provider = MagicMock(spec=SQLAlchemyProvider)

            with patch('ncm_foundation.core.database.manager.DatabaseFactory.create_provider', return_value=mock_provider):
                db_manager = DatabaseManager(self.config)

                assert hasattr(db_manager, 'transaction_manager')
                assert hasattr(db_manager, 'nested_transaction_manager')
                assert db_manager.transaction_manager is not None

    def test_migration_manager_initialization(self):
        """Test migration manager is properly initialized for PostgreSQL."""
        with patch('ncm_foundation.core.database.providers.sqlalchemy_provider.create_async_engine') as mock_engine:
            mock_engine.return_value = MagicMock()
            mock_provider = MagicMock(spec=SQLAlchemyProvider)

            with patch('ncm_foundation.core.database.manager.DatabaseFactory.create_provider', return_value=mock_provider):
                db_manager = DatabaseManager(self.config)

                assert hasattr(db_manager, 'migration_manager')
                assert db_manager.migration_manager is not None
