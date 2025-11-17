"""
SQLAlchemy repository implementation.
"""

import logging
from typing import Any, Dict, List, Optional, Type, TypeVar

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.base import BaseModel, SoftDeleteMixin
from .base import AbstractRepository

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class SQLAlchemyRepository(AbstractRepository[T]):
    """SQLAlchemy repository implementation."""

    def __init__(self, model_class: Type[T], session: AsyncSession):
        super().__init__(model_class)
        self.session = session

    async def _ensure_session(self):
        """Ensure session is available."""
        if self.session is None:
            self.session = await self.db_manager.get_session()

    async def create(self, data: Dict[str, Any]) -> T:
        """Create entity."""
        try:
            instance = self.model_class(**data)
            self.session.add(instance)
            await self.session.commit()
            await self.session.refresh(instance)
            return instance
        except IntegrityError as e:
            await self.session.rollback()
            logger.error(
                f"Integrity error creating {self.model_class.__name__}: {e}")
            raise
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error creating {self.model_class.__name__}: {e}")
            raise

    async def get_by_id(self, id: Any) -> Optional[T]:
        """Get entity by ID."""
        try:
            query = select(self.model_class).where(self.model_class.id == id)

            # Apply soft delete filter if model supports it
            if issubclass(self.model_class, SoftDeleteMixin):
                query = query.where(self.model_class.is_deleted == False)

            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(
                f"Error getting {self.model_class.__name__} by ID {id}: {e}")
            raise

    async def update(self, id: Any, data: Dict[str, Any]) -> Optional[T]:
        """Update entity."""
        try:
            # Get existing entity
            entity = await self.get_by_id(id)
            if not entity:
                return None

            # Update fields
            for key, value in data.items():
                if hasattr(entity, key):
                    setattr(entity, key, value)

            await self.session.commit()
            await self.session.refresh(entity)
            return entity
        except Exception as e:
            await self.session.rollback()
            logger.error(
                f"Error updating {self.model_class.__name__} {id}: {e}")
            raise

    async def delete(self, id: Any) -> bool:
        """Delete entity."""
        try:
            entity = await self.get_by_id(id)
            if not entity:
                return False

            # Handle soft delete
            if issubclass(self.model_class, SoftDeleteMixin):
                entity.soft_delete("system")
                await self.session.commit()
            else:
                # Hard delete
                query = delete(self.model_class).where(
                    self.model_class.id == id)
                await self.session.execute(query)
                await self.session.commit()

            return True
        except Exception as e:
            await self.session.rollback()
            logger.error(
                f"Error deleting {self.model_class.__name__} {id}: {e}")
            raise

    async def list(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
        order_by: Optional[str] = None,
    ) -> List[T]:
        """List entities with filtering."""
        try:
            query = select(self.model_class)

            # Apply soft delete filter
            if issubclass(self.model_class, SoftDeleteMixin):
                query = query.where(self.model_class.is_deleted == False)

            # Apply filters
            if filters:
                query = self._apply_filters(query, filters)

            # Apply ordering
            if order_by:
                query = self._apply_ordering(query, order_by)
            else:
                query = query.order_by(self.model_class.created_at.desc())

            # Apply pagination
            query = query.limit(limit).offset(offset)

            result = await self.session.execute(query)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error listing {self.model_class.__name__}: {e}")
            raise

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count entities."""
        try:
            query = select(func.count(self.model_class.id))

            # Apply soft delete filter
            if issubclass(self.model_class, SoftDeleteMixin):
                query = query.where(self.model_class.is_deleted == False)

            # Apply filters
            if filters:
                query = self._apply_filters(query, filters)

            result = await self.session.execute(query)
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"Error counting {self.model_class.__name__}: {e}")
            raise

    async def exists(self, id: Any) -> bool:
        """Check if entity exists."""
        try:
            query = select(self.model_class.id).where(
                self.model_class.id == id)

            # Apply soft delete filter
            if issubclass(self.model_class, SoftDeleteMixin):
                query = query.where(self.model_class.is_deleted == False)

            result = await self.session.execute(query)
            return result.scalar() is not None
        except Exception as e:
            logger.error(
                f"Error checking existence of {self.model_class.__name__} {id}: {e}"
            )
            raise

    async def bulk_create(self, data_list: List[Dict[str, Any]]) -> List[T]:
        """Create multiple entities."""
        try:
            instances = [self.model_class(**data) for data in data_list]
            self.session.add_all(instances)
            await self.session.commit()

            # Refresh all instances
            for instance in instances:
                await self.session.refresh(instance)

            return instances
        except Exception as e:
            await self.session.rollback()
            logger.error(
                f"Error bulk creating {self.model_class.__name__}: {e}")
            raise

    async def bulk_update(self, updates: List[Dict[str, Any]]) -> int:
        """Update multiple entities."""
        try:
            updated_count = 0
            for update_data in updates:
                id = update_data.pop("id")
                if await self.update(id, update_data):
                    updated_count += 1
            return updated_count
        except Exception as e:
            logger.error(
                f"Error bulk updating {self.model_class.__name__}: {e}")
            raise

    async def bulk_delete(self, ids: List[Any]) -> int:
        """Delete multiple entities."""
        try:
            deleted_count = 0
            for id in ids:
                if await self.delete(id):
                    deleted_count += 1
            return deleted_count
        except Exception as e:
            logger.error(
                f"Error bulk deleting {self.model_class.__name__}: {e}")
            raise

    async def search(
        self,
        query: str,
        fields: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[T]:
        """Search entities."""
        try:
            # This is a basic implementation - can be enhanced with full-text search
            search_query = select(self.model_class)

            # Apply soft delete filter
            if issubclass(self.model_class, SoftDeleteMixin):
                search_query = search_query.where(
                    self.model_class.is_deleted == False)

            # Build search conditions
            conditions = []
            if fields:
                for field in fields:
                    if hasattr(self.model_class, field):
                        column = getattr(self.model_class, field)
                        conditions.append(column.ilike(f"%{query}%"))
            else:
                # Search in common text fields
                for column in self.model_class.__table__.columns:
                    if column.type.python_type == str:
                        conditions.append(column.ilike(f"%{query}%"))

            if conditions:
                search_query = search_query.where(or_(*conditions))

            search_query = search_query.limit(limit).offset(offset)

            result = await self.session.execute(search_query)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error searching {self.model_class.__name__}: {e}")
            raise

    async def get_by_field(self, field: str, value: Any) -> Optional[T]:
        """Get entity by field value."""
        try:
            if not hasattr(self.model_class, field):
                raise ValueError(
                    f"Field {field} does not exist on {self.model_class.__name__}"
                )

            query = select(self.model_class).where(
                getattr(self.model_class, field) == value
            )

            # Apply soft delete filter
            if issubclass(self.model_class, SoftDeleteMixin):
                query = query.where(self.model_class.is_deleted == False)

            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(
                f"Error getting {self.model_class.__name__} by {field}={value}: {e}"
            )
            raise

    async def get_by_fields(self, filters: Dict[str, Any]) -> Optional[T]:
        """Get entity by multiple field values."""
        try:
            query = select(self.model_class)

            # Apply soft delete filter
            if issubclass(self.model_class, SoftDeleteMixin):
                query = query.where(self.model_class.is_deleted == False)

            # Apply filters
            query = self._apply_filters(query, filters)

            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(
                f"Error getting {self.model_class.__name__} by fields: {e}")
            raise

    async def list_by_field(
        self, field: str, value: Any, limit: int = 100, offset: int = 0
    ) -> List[T]:
        """List entities by field value."""
        try:
            if not hasattr(self.model_class, field):
                raise ValueError(
                    f"Field {field} does not exist on {self.model_class.__name__}"
                )

            query = select(self.model_class).where(
                getattr(self.model_class, field) == value
            )

            # Apply soft delete filter
            if issubclass(self.model_class, SoftDeleteMixin):
                query = query.where(self.model_class.is_deleted == False)

            query = query.limit(limit).offset(offset)

            result = await self.session.execute(query)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(
                f"Error listing {self.model_class.__name__} by {field}={value}: {e}"
            )
            raise

    async def list_by_fields(
        self, filters: Dict[str, Any], limit: int = 100, offset: int = 0
    ) -> List[T]:
        """List entities by multiple field values."""
        try:
            query = select(self.model_class)

            # Apply soft delete filter
            if issubclass(self.model_class, SoftDeleteMixin):
                query = query.where(self.model_class.is_deleted == False)

            # Apply filters
            query = self._apply_filters(query, filters)
            query = query.limit(limit).offset(offset)

            result = await self.session.execute(query)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(
                f"Error listing {self.model_class.__name__} by fields: {e}")
            raise

    def _apply_filters(self, query, filters: Dict[str, Any]):
        """Apply filters to query."""
        conditions = []

        for field, value in filters.items():
            if hasattr(self.model_class, field):
                column = getattr(self.model_class, field)

                if isinstance(value, list):
                    # IN clause
                    conditions.append(column.in_(value))
                elif isinstance(value, dict):
                    # Range or comparison operators
                    if "gte" in value:
                        conditions.append(column >= value["gte"])
                    if "lte" in value:
                        conditions.append(column <= value["lte"])
                    if "gt" in value:
                        conditions.append(column > value["gt"])
                    if "lt" in value:
                        conditions.append(column < value["lt"])
                    if "like" in value:
                        conditions.append(column.like(f"%{value['like']}%"))
                    if "ilike" in value:
                        conditions.append(column.ilike(f"%{value['ilike']}%"))
                else:
                    # Exact match
                    conditions.append(column == value)

        if conditions:
            query = query.where(and_(*conditions))

        return query

    def _apply_ordering(self, query, order_by: str):
        """Apply ordering to query."""
        if order_by.startswith("-"):
            # Descending order
            field = order_by[1:]
            if hasattr(self.model_class, field):
                column = getattr(self.model_class, field)
                query = query.order_by(column.desc())
        else:
            # Ascending order
            if hasattr(self.model_class, order_by):
                column = getattr(self.model_class, order_by)
                query = query.order_by(column.asc())

        return query
