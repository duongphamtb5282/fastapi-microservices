"""
Database entity implementations with audit support.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from .interfaces import AuditLogger, BaseEntity

logger = logging.getLogger(__name__)


class AuditLoggerImpl(AuditLogger):
    """Audit logger implementation."""

    def __init__(self, audit_collection: str = "audit_logs"):
        self.audit_collection = audit_collection
        self._audit_entries: List[Dict[str, Any]] = []

    async def log_create(self, entity: BaseEntity, user_id: str) -> None:
        """Log entity creation."""
        audit_entry = {
            "action": "CREATE",
            "entity_type": entity.__class__.__name__,
            "entity_id": entity.id,
            "user_id": user_id,
            "timestamp": datetime.utcnow(),
            "changes": entity.to_dict(),
            "metadata": {
                "created_at": entity.created_at,
                "created_by": entity.created_by,
            },
        }

        self._audit_entries.append(audit_entry)
        logger.info(
            f"Audit log: CREATE {entity.__class__.__name__} {entity.id} by {user_id}"
        )

    async def log_update(self, entity: BaseEntity, changes: Dict, user_id: str) -> None:
        """Log entity update."""
        audit_entry = {
            "action": "UPDATE",
            "entity_type": entity.__class__.__name__,
            "entity_id": entity.id,
            "user_id": user_id,
            "timestamp": datetime.utcnow(),
            "changes": changes,
            "metadata": {
                "version": entity.version,
                "updated_at": entity.updated_at,
                "updated_by": entity.updated_by,
            },
        }

        self._audit_entries.append(audit_entry)
        logger.info(
            f"Audit log: UPDATE {entity.__class__.__name__} {entity.id} by {user_id}"
        )

    async def log_delete(self, entity: BaseEntity, user_id: str) -> None:
        """Log entity deletion."""
        audit_entry = {
            "action": "DELETE",
            "entity_type": entity.__class__.__name__,
            "entity_id": entity.id,
            "user_id": user_id,
            "timestamp": datetime.utcnow(),
            "changes": entity.to_dict(),
            "metadata": {"deleted_at": datetime.utcnow(), "deleted_by": user_id},
        }

        self._audit_entries.append(audit_entry)
        logger.info(
            f"Audit log: DELETE {entity.__class__.__name__} {entity.id} by {user_id}"
        )

    def get_audit_entries(self) -> List[Dict[str, Any]]:
        """Get all audit entries."""
        return self._audit_entries.copy()

    def clear_audit_entries(self) -> None:
        """Clear all audit entries."""
        self._audit_entries.clear()


class AuditableEntity(BaseEntity):
    """Auditable entity with enhanced audit capabilities."""

    def __init__(
        self,
        id: Optional[Any] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        created_by: Optional[str] = None,
        updated_by: Optional[str] = None,
        version: int = 1,
        audit_logger: Optional[AuditLogger] = None,
    ):
        super().__init__(id, created_at, updated_at, created_by, updated_by, version)
        self.audit_logger = audit_logger
        self._original_data: Optional[Dict[str, Any]] = None

    def set_original_data(self, data: Dict[str, Any]) -> None:
        """Set original data for change tracking."""
        self._original_data = data.copy()

    def get_changes(self) -> Dict[str, Any]:
        """Get changes from original data."""
        if not self._original_data:
            return {}

        current_data = self.to_dict()
        changes = {}

        for key, value in current_data.items():
            if key not in self._original_data or self._original_data[key] != value:
                changes[key] = {"old": self._original_data.get(key), "new": value}

        return changes

    async def log_creation(self, user_id: str) -> None:
        """Log entity creation."""
        if self.audit_logger:
            await self.audit_logger.log_create(self, user_id)

    async def log_update(self, user_id: str) -> None:
        """Log entity update."""
        if self.audit_logger:
            changes = self.get_changes()
            if changes:
                await self.audit_logger.log_update(self, changes, user_id)

    async def log_deletion(self, user_id: str) -> None:
        """Log entity deletion."""
        if self.audit_logger:
            await self.audit_logger.log_delete(self, user_id)


class SoftDeleteEntity(AuditableEntity):
    """Entity with soft delete capability."""

    def __init__(
        self,
        id: Optional[Any] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        created_by: Optional[str] = None,
        updated_by: Optional[str] = None,
        version: int = 1,
        audit_logger: Optional[AuditLogger] = None,
        deleted_at: Optional[datetime] = None,
        deleted_by: Optional[str] = None,
        is_deleted: bool = False,
    ):
        super().__init__(
            id, created_at, updated_at, created_by, updated_by, version, audit_logger
        )
        self.deleted_at = deleted_at
        self.deleted_by = deleted_by
        self.is_deleted = is_deleted

    def soft_delete(self, user_id: str) -> None:
        """Soft delete the entity."""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
        self.deleted_by = user_id
        self.update_audit_fields(user_id)

    def restore(self, user_id: str) -> None:
        """Restore the entity."""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.update_audit_fields(user_id)

    def to_dict(self) -> Dict[str, Any]:
        """Convert entity to dictionary."""
        data = super().to_dict()
        data.update(
            {
                "deleted_at": self.deleted_at,
                "deleted_by": self.deleted_by,
                "is_deleted": self.is_deleted,
            }
        )
        return data


class VersionedEntity(AuditableEntity):
    """Entity with version control."""

    def __init__(
        self,
        id: Optional[Any] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        created_by: Optional[str] = None,
        updated_by: Optional[str] = None,
        version: int = 1,
        audit_logger: Optional[AuditLogger] = None,
        version_history: Optional[List[Dict[str, Any]]] = None,
    ):
        super().__init__(
            id, created_at, updated_at, created_by, updated_by, version, audit_logger
        )
        self.version_history = version_history or []

    def create_version_snapshot(self, user_id: str) -> None:
        """Create a version snapshot."""
        snapshot = {
            "version": self.version,
            "data": self.to_dict(),
            "created_at": datetime.utcnow(),
            "created_by": user_id,
        }
        self.version_history.append(snapshot)

    def get_version(self, version: int) -> Optional[Dict[str, Any]]:
        """Get entity data for a specific version."""
        for snapshot in self.version_history:
            if snapshot["version"] == version:
                return snapshot["data"]
        return None

    def get_latest_version(self) -> int:
        """Get the latest version number."""
        if not self.version_history:
            return self.version
        return max(snapshot["version"] for snapshot in self.version_history)

    def rollback_to_version(self, version: int, user_id: str) -> bool:
        """Rollback to a specific version."""
        target_snapshot = None
        for snapshot in self.version_history:
            if snapshot["version"] == version:
                target_snapshot = snapshot
                break

        if not target_snapshot:
            return False

        # Restore data from snapshot
        snapshot_data = target_snapshot["data"]
        for key, value in snapshot_data.items():
            if key not in ["version", "created_at", "updated_at"]:
                setattr(self, key, value)

        self.version = version
        self.update_audit_fields(user_id)

        return True
