"""Base service interface and implementation."""

from typing import Generic, TypeVar, Optional, Type
from ncm_foundation.core.database import SQLAlchemyRepository, DatabaseManager
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar('T')
R = TypeVar('R', bound=SQLAlchemyRepository)


class DatabaseService:
    """Base service with common database functionality."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None, cache_manager=None):
        # Store database manager (may be None during import time)
        self.db_manager = db_manager
        self.cache_manager = cache_manager

        # Get transaction managers from database manager (if available)
        if db_manager:
            self.transaction_manager = db_manager.get_transaction_manager()
            self.nested_transaction_manager = db_manager.get_nested_transaction_manager()
        else:
            self.transaction_manager = None
            self.nested_transaction_manager = None


class BaseService(DatabaseService, Generic[T, R]):
    """Base service interface."""

    def __init__(
        self,
        repository: Optional[R] = None,
        repository_class: Optional[Type[R]] = None,
        db_manager: Optional[DatabaseManager] = None,
        session: Optional[AsyncSession] = None,
        cache_manager=None,
    ):
        # Initialize database functionality first
        DatabaseService.__init__(self, db_manager, cache_manager)
        # Store session for repository creation
        self.session = session
        # Store repository class for later instantiation
        self._repository_class = repository_class
        # Initialize with repository instance (may be None, will be set by property)
        self._repository = repository

        # If we have a session but no db_manager, try to get db_manager from DI container
        if session is not None and db_manager is None:
            try:
                from ncm_sample.core.container import get_container
                container = get_container()
                self.db_manager = container.get(DatabaseManager)
                # Re-initialize transaction managers with the db_manager
                if self.db_manager:
                    self.transaction_manager = self.db_manager.get_transaction_manager()
                    self.nested_transaction_manager = self.db_manager.get_nested_transaction_manager()
            except Exception as e:
                # If we can't get db_manager from container, the transaction manager will remain None
                # and the @with_transaction decorator will fall back to executing without transaction
                print(f"Warning: Could not get db_manager from container: {e}")

    @property
    def repository(self) -> R:
        """Get repository, creating it if needed."""
        if self._repository is None and self._repository_class is not None:
            # Create repository instance using the repository class
            if self.session is not None:
                # Pass session and cache_manager to repository constructor
                self._repository = self._repository_class(self.session, self.cache_manager)
            else:
                # Try to get database manager from container
                try:
                    from ncm_sample.core.container import get_container
                    container = get_container()
                    db_manager = container.get(DatabaseManager)
                    # Pass the db_manager and cache_manager to repository constructor
                    self._repository = self._repository_class(db_manager, self.cache_manager)
                except Exception:
                    raise RuntimeError(
                        "Cannot create repository: no session or database manager available"
                    )

        if self._repository is None:
            raise RuntimeError("Repository not available")

        return self._repository

    @repository.setter
    def repository(self, value: R):
        """Set repository."""
        self._repository = value

    async def get_repository(self) -> R:
        """Get repository, creating it if needed."""
        return self.repository
