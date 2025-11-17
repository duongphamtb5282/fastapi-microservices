"""
MongoDB repository implementation.
"""

import logging
from typing import Any, Dict, List, Optional, Type, TypeVar

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase

from .base import AbstractRepository

logger = logging.getLogger(__name__)
T = TypeVar("T")


class MongoDBRepository(AbstractRepository[T]):
    """MongoDB repository implementation."""

    def __init__(
        self, model_class: Type[T], database: AsyncIOMotorDatabase, collection_name: str
    ):
        super().__init__(model_class)
        self.database = database
        self.collection_name = collection_name
        self.collection: AsyncIOMotorCollection = database[collection_name]

    async def create(self, data: Dict[str, Any]) -> T:
        """Create entity."""
        try:
            result = await self.collection.insert_one(data)
            data["_id"] = result.inserted_id

            # Create model instance
            instance = self.model_class(**data)
            return instance
        except Exception as e:
            logger.error(f"Error creating {self.model_class.__name__}: {e}")
            raise

    async def get_by_id(self, id: Any) -> Optional[T]:
        """Get entity by ID."""
        try:
            # Convert string ID to ObjectId if needed
            if isinstance(id, str):
                try:
                    id = ObjectId(id)
                except InvalidId:
                    return None

            document = await self.collection.find_one({"_id": id})
            if not document:
                return None

            # Convert MongoDB document to model instance
            document["id"] = str(document.pop("_id"))
            instance = self.model_class(**document)
            return instance
        except Exception as e:
            logger.error(f"Error getting {self.model_class.__name__} by ID {id}: {e}")
            raise

    async def update(self, id: Any, data: Dict[str, Any]) -> Optional[T]:
        """Update entity."""
        try:
            # Convert string ID to ObjectId if needed
            if isinstance(id, str):
                try:
                    id = ObjectId(id)
                except InvalidId:
                    return None

            # Remove None values from update data
            update_data = {k: v for k, v in data.items() if v is not None}

            result = await self.collection.update_one(
                {"_id": id}, {"$set": update_data}
            )

            if result.matched_count == 0:
                return None

            # Return updated entity
            return await self.get_by_id(id)
        except Exception as e:
            logger.error(f"Error updating {self.model_class.__name__} {id}: {e}")
            raise

    async def delete(self, id: Any) -> bool:
        """Delete entity."""
        try:
            # Convert string ID to ObjectId if needed
            if isinstance(id, str):
                try:
                    id = ObjectId(id)
                except InvalidId:
                    return False

            result = await self.collection.delete_one({"_id": id})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting {self.model_class.__name__} {id}: {e}")
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
            # Build MongoDB query
            query = {}
            if filters:
                query = self._build_mongo_query(filters)

            # Build sort criteria
            sort_criteria = []
            if order_by:
                if order_by.startswith("-"):
                    sort_criteria.append((order_by[1:], -1))
                else:
                    sort_criteria.append((order_by, 1))
            else:
                sort_criteria.append(("created_at", -1))

            # Execute query
            cursor = (
                self.collection.find(query)
                .sort(sort_criteria)
                .skip(offset)
                .limit(limit)
            )
            documents = await cursor.to_list(length=limit)

            # Convert to model instances
            instances = []
            for doc in documents:
                doc["id"] = str(doc.pop("_id"))
                instance = self.model_class(**doc)
                instances.append(instance)

            return instances
        except Exception as e:
            logger.error(f"Error listing {self.model_class.__name__}: {e}")
            raise

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count entities."""
        try:
            query = {}
            if filters:
                query = self._build_mongo_query(filters)

            count = await self.collection.count_documents(query)
            return count
        except Exception as e:
            logger.error(f"Error counting {self.model_class.__name__}: {e}")
            raise

    async def exists(self, id: Any) -> bool:
        """Check if entity exists."""
        try:
            # Convert string ID to ObjectId if needed
            if isinstance(id, str):
                try:
                    id = ObjectId(id)
                except InvalidId:
                    return False

            count = await self.collection.count_documents({"_id": id}, limit=1)
            return count > 0
        except Exception as e:
            logger.error(
                f"Error checking existence of {self.model_class.__name__} {id}: {e}"
            )
            raise

    async def bulk_create(self, data_list: List[Dict[str, Any]]) -> List[T]:
        """Create multiple entities."""
        try:
            result = await self.collection.insert_many(data_list)

            # Get created documents
            instances = []
            for i, doc in enumerate(data_list):
                doc["_id"] = result.inserted_ids[i]
                doc["id"] = str(doc.pop("_id"))
                instance = self.model_class(**doc)
                instances.append(instance)

            return instances
        except Exception as e:
            logger.error(f"Error bulk creating {self.model_class.__name__}: {e}")
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
            logger.error(f"Error bulk updating {self.model_class.__name__}: {e}")
            raise

    async def bulk_delete(self, ids: List[Any]) -> int:
        """Delete multiple entities."""
        try:
            # Convert string IDs to ObjectIds
            object_ids = []
            for id in ids:
                if isinstance(id, str):
                    try:
                        object_ids.append(ObjectId(id))
                    except InvalidId:
                        continue
                else:
                    object_ids.append(id)

            if not object_ids:
                return 0

            result = await self.collection.delete_many({"_id": {"$in": object_ids}})
            return result.deleted_count
        except Exception as e:
            logger.error(f"Error bulk deleting {self.model_class.__name__}: {e}")
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
            # Build text search query
            search_query = {"$text": {"$search": query}}

            # If specific fields are provided, use regex search instead
            if fields:
                search_query = {
                    "$or": [
                        {field: {"$regex": query, "$options": "i"}} for field in fields
                    ]
                }

            cursor = self.collection.find(search_query).skip(offset).limit(limit)
            documents = await cursor.to_list(length=limit)

            # Convert to model instances
            instances = []
            for doc in documents:
                doc["id"] = str(doc.pop("_id"))
                instance = self.model_class(**doc)
                instances.append(instance)

            return instances
        except Exception as e:
            logger.error(f"Error searching {self.model_class.__name__}: {e}")
            raise

    async def get_by_field(self, field: str, value: Any) -> Optional[T]:
        """Get entity by field value."""
        try:
            document = await self.collection.find_one({field: value})
            if not document:
                return None

            document["id"] = str(document.pop("_id"))
            instance = self.model_class(**document)
            return instance
        except Exception as e:
            logger.error(
                f"Error getting {self.model_class.__name__} by {field}={value}: {e}"
            )
            raise

    async def get_by_fields(self, filters: Dict[str, Any]) -> Optional[T]:
        """Get entity by multiple field values."""
        try:
            query = self._build_mongo_query(filters)
            document = await self.collection.find_one(query)
            if not document:
                return None

            document["id"] = str(document.pop("_id"))
            instance = self.model_class(**document)
            return instance
        except Exception as e:
            logger.error(f"Error getting {self.model_class.__name__} by fields: {e}")
            raise

    async def list_by_field(
        self, field: str, value: Any, limit: int = 100, offset: int = 0
    ) -> List[T]:
        """List entities by field value."""
        try:
            cursor = self.collection.find({field: value}).skip(offset).limit(limit)
            documents = await cursor.to_list(length=limit)

            # Convert to model instances
            instances = []
            for doc in documents:
                doc["id"] = str(doc.pop("_id"))
                instance = self.model_class(**doc)
                instances.append(instance)

            return instances
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
            query = self._build_mongo_query(filters)
            cursor = self.collection.find(query).skip(offset).limit(limit)
            documents = await cursor.to_list(length=limit)

            # Convert to model instances
            instances = []
            for doc in documents:
                doc["id"] = str(doc.pop("_id"))
                instance = self.model_class(**doc)
                instances.append(instance)

            return instances
        except Exception as e:
            logger.error(f"Error listing {self.model_class.__name__} by fields: {e}")
            raise

    def _build_mongo_query(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Build MongoDB query from filters."""
        query = {}

        for field, value in filters.items():
            if isinstance(value, list):
                # IN clause
                query[field] = {"$in": value}
            elif isinstance(value, dict):
                # Range or comparison operators
                field_query = {}
                if "gte" in value:
                    field_query["$gte"] = value["gte"]
                if "lte" in value:
                    field_query["$lte"] = value["lte"]
                if "gt" in value:
                    field_query["$gt"] = value["gt"]
                if "lt" in value:
                    field_query["$lt"] = value["lt"]
                if "regex" in value:
                    field_query["$regex"] = value["regex"]
                    field_query["$options"] = value.get("options", "i")

                if field_query:
                    query[field] = field_query
            else:
                # Exact match
                query[field] = value

        return query
