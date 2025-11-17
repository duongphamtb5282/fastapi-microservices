"""
Abstract repository interface.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from pydantic import BaseModel

T = TypeVar("T")
S = TypeVar("S", bound=BaseModel)


class AbstractRepository(ABC, Generic[T]):
    """Abstract repository interface."""

    def __init__(self, model_class: Type[T]):
        self.model_class = model_class

    @abstractmethod
    async def create(self, data: Dict[str, Any]) -> T:
        """Create entity."""
        pass

    @abstractmethod
    async def get_by_id(self, id: Any) -> Optional[T]:
        """Get entity by ID."""
        pass

    @abstractmethod
    async def update(self, id: Any, data: Dict[str, Any]) -> Optional[T]:
        """Update entity."""
        pass

    @abstractmethod
    async def delete(self, id: Any) -> bool:
        """Delete entity."""
        pass

    @abstractmethod
    async def list(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
        order_by: Optional[str] = None,
    ) -> List[T]:
        """List entities with filtering."""
        pass

    @abstractmethod
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count entities."""
        pass

    @abstractmethod
    async def exists(self, id: Any) -> bool:
        """Check if entity exists."""
        pass

    @abstractmethod
    async def bulk_create(self, data_list: List[Dict[str, Any]]) -> List[T]:
        """Create multiple entities."""
        pass

    @abstractmethod
    async def bulk_update(self, updates: List[Dict[str, Any]]) -> int:
        """Update multiple entities."""
        pass

    @abstractmethod
    async def bulk_delete(self, ids: List[Any]) -> int:
        """Delete multiple entities."""
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        fields: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[T]:
        """Search entities."""
        pass

    @abstractmethod
    async def get_by_field(self, field: str, value: Any) -> Optional[T]:
        """Get entity by field value."""
        pass

    @abstractmethod
    async def get_by_fields(self, filters: Dict[str, Any]) -> Optional[T]:
        """Get entity by multiple field values."""
        pass

    @abstractmethod
    async def list_by_field(
        self, field: str, value: Any, limit: int = 100, offset: int = 0
    ) -> List[T]:
        """List entities by field value."""
        pass

    @abstractmethod
    async def list_by_fields(
        self, filters: Dict[str, Any], limit: int = 100, offset: int = 0
    ) -> List[T]:
        """List entities by multiple field values."""
        pass

    def _apply_filters(self, query, filters: Dict[str, Any]):
        """Apply filters to query (to be implemented by subclasses)."""
        return query

    def _apply_ordering(self, query, order_by: Optional[str]):
        """Apply ordering to query (to be implemented by subclasses)."""
        return query

    def _apply_pagination(self, query, limit: int, offset: int):
        """Apply pagination to query (to be implemented by subclasses)."""
        return query
