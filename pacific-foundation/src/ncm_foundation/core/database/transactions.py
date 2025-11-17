"""
Transaction management system.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

from .interfaces import Savepoint, Transaction
from .providers import DatabaseSavepoint, DatabaseTransaction

logger = logging.getLogger(__name__)


class TransactionManager:
    """Transaction manager for database operations."""

    def __init__(self, provider: Any):
        self.provider = provider
        self._active_transactions: Dict[str, Transaction] = {}
        self._transaction_counter = 0

    def _generate_transaction_id(self) -> str:
        """Generate unique transaction ID."""
        self._transaction_counter += 1
        return f"tx_{self._transaction_counter}_{id(self)}"

    @asynccontextmanager
    async def get_transaction(self, transaction_id: Optional[str] = None)-> None:
        """Get transaction context manager."""
        if not transaction_id:
            transaction_id = self._generate_transaction_id()

        transaction = DatabaseTransaction(self.provider)
        self._active_transactions[transaction_id] = transaction

        try:
            async with transaction:
                yield transaction
        finally:
            if transaction_id in self._active_transactions:
                del self._active_transactions[transaction_id]

    async def execute_in_transaction(
        self, operations: List[Callable], transaction_id: Optional[str] = None
    ) -> List[Any]:
        """Execute multiple operations in a transaction."""
        results = []

        async with self.get_transaction(transaction_id) as transaction:
            for operation in operations:
                try:
                    if asyncio.iscoroutinefunction(operation):
                        result = await operation()
                    else:
                        result = operation()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Operation failed in transaction: {e}")
                    raise

        return results

    def get_active_transactions(self) -> Dict[str, Transaction]:
        """Get active transactions."""
        return self._active_transactions.copy()

    def is_transaction_active(self, transaction_id: str) -> bool:
        """Check if transaction is active."""
        return transaction_id in self._active_transactions


class NestedTransactionManager:
    """Nested transaction manager with savepoint support."""

    def __init__(self, provider: Any):
        self.provider = provider
        self._transaction_stack: List[Transaction] = []
        self._savepoint_stack: List[Savepoint] = []

    @asynccontextmanager
    async def begin_nested(self):
        """Begin nested transaction."""
        if not self._transaction_stack:
            # Start root transaction
            transaction = DatabaseTransaction(self.provider)
            async with transaction:
                self._transaction_stack.append(transaction)
                try:
                    yield transaction
                finally:
                    self._transaction_stack.clear()
        else:
            # Create savepoint
            current_transaction = self._transaction_stack[-1]
            savepoint = await current_transaction.savepoint(
                f"sp_{len(self._savepoint_stack)}"
            )
            self._savepoint_stack.append(savepoint)

            try:
                yield savepoint
            except Exception:
                await savepoint.rollback()
                raise
            finally:
                if self._savepoint_stack:
                    self._savepoint_stack.pop()

    async def commit_nested(self) -> None:
        """Commit nested transaction."""
        if self._savepoint_stack:
            savepoint = self._savepoint_stack.pop()
            await savepoint.commit()
        elif self._transaction_stack:
            transaction = self._transaction_stack[-1]
            await transaction.commit()

    async def rollback_nested(self) -> None:
        """Rollback nested transaction."""
        if self._savepoint_stack:
            savepoint = self._savepoint_stack.pop()
            await savepoint.rollback()
        elif self._transaction_stack:
            transaction = self._transaction_stack[-1]
            await transaction.rollback()

    def get_nesting_level(self) -> int:
        """Get current nesting level."""
        return len(self._transaction_stack) + len(self._savepoint_stack)

    def is_nested(self) -> bool:
        """Check if currently in nested transaction."""
        return len(self._transaction_stack) > 1 or len(self._savepoint_stack) > 0


def transactional(func: Callable) -> Callable:
    """Decorator for automatic transaction management."""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract transaction manager from args or kwargs
        transaction_manager = None

        # Look for transaction_manager in kwargs
        if "transaction_manager" in kwargs:
            transaction_manager = kwargs.pop("transaction_manager")

        # Look for transaction_manager in args (assuming it's the first arg)
        elif args and hasattr(args[0], "transaction_manager"):
            transaction_manager = args[0].transaction_manager

        if not transaction_manager:
            raise ValueError("Transaction manager not found")

        async with transaction_manager.get_transaction():
            return await func(*args, **kwargs)

    return wrapper


def requires_transaction(func: Callable) -> Callable:
    """Decorator to ensure function runs within a transaction."""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Check if we're already in a transaction
        transaction_manager = None

        if "transaction_manager" in kwargs:
            transaction_manager = kwargs["transaction_manager"]
        elif args and hasattr(args[0], "transaction_manager"):
            transaction_manager = args[0].transaction_manager

        if not transaction_manager:
            raise ValueError("Transaction manager not found")

        if not transaction_manager._active_transactions:
            raise RuntimeError("Function requires an active transaction")

        return await func(*args, **kwargs)

    return wrapper


class TransactionContext:
    """Transaction context for managing transaction state."""

    def __init__(self):
        self._transaction_id: Optional[str] = None
        self._is_rollback_only = False

    def set_transaction_id(self, transaction_id: str) -> None:
        """Set transaction ID."""
        self._transaction_id = transaction_id

    def get_transaction_id(self) -> Optional[str]:
        """Get transaction ID."""
        return self._transaction_id

    def set_rollback_only(self) -> None:
        """Mark transaction for rollback only."""
        self._is_rollback_only = True

    def is_rollback_only(self) -> bool:
        """Check if transaction is marked for rollback only."""
        return self._is_rollback_only

    def clear(self) -> None:
        """Clear transaction context."""
        self._transaction_id = None
        self._is_rollback_only = False


# Global transaction context
_transaction_context = TransactionContext()


def get_transaction_context() -> TransactionContext:
    """Get global transaction context."""
    return _transaction_context


def set_transaction_context(transaction_id: str) -> None:
    """Set transaction context."""
    _transaction_context.set_transaction_id(transaction_id)


def clear_transaction_context() -> None:
    """Clear transaction context."""
    _transaction_context.clear()
