"""Test cases for database transactions."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from ncm_foundation.core.database.transactions import TransactionManager
from ncm_foundation.core.database.providers.sqlalchemy_provider import SQLAlchemyProvider


class TestTransactionManager:
    """Test TransactionManager functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        mock_provider = MagicMock(spec=SQLAlchemyProvider)
        mock_provider.get_connection = AsyncMock()
        mock_provider.return_connection = AsyncMock()

        self.transaction_manager = TransactionManager(mock_provider)

    @pytest.mark.asyncio
    async def test_transaction_manager_initialization(self):
        """Test TransactionManager can be initialized."""
        assert self.transaction_manager.provider is not None
        assert self.transaction_manager._active_transactions == {}
        assert self.transaction_manager._transaction_counter == 0

    @pytest.mark.asyncio
    async def test_get_transaction(self):
        """Test getting a transaction."""
        # Mock the DatabaseTransaction
        mock_transaction = MagicMock()
        mock_transaction.__aenter__ = AsyncMock(return_value=mock_transaction)
        mock_transaction.__aexit__ = AsyncMock()

        with patch('ncm_foundation.core.database.transactions.DatabaseTransaction', return_value=mock_transaction):
            async with self.transaction_manager.get_transaction() as tx:
                assert tx == mock_transaction

    @pytest.mark.asyncio
    async def test_transaction_id_generation(self):
        """Test transaction ID generation."""
        tx1 = self.transaction_manager._generate_transaction_id()
        tx2 = self.transaction_manager._generate_transaction_id()

        assert tx1 != tx2
        assert tx1.startswith("tx_")
        assert tx2.startswith("tx_")

    @pytest.mark.asyncio
    async def test_execute_in_transaction(self):
        """Test executing operations in transaction."""
        async def operation1():
            return "result1"

        async def operation2():
            return "result2"

        operations = [operation1, operation2]

        # Mock the transaction context
        mock_transaction = MagicMock()
        mock_transaction.__aenter__ = AsyncMock(return_value=mock_transaction)
        mock_transaction.__aexit__ = AsyncMock()

        with patch('ncm_foundation.core.database.transactions.DatabaseTransaction', return_value=mock_transaction):
            results = await self.transaction_manager.execute_in_transaction(operations)

            assert len(results) == 2
            assert results[0] == "result1"
            assert results[1] == "result2"
