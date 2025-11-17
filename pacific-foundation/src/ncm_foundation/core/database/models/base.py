"""
Base SQLAlchemy models with audit capabilities.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.ext.hybrid import hybrid_property

# Create declarative base
Base = declarative_base()


class TimestampMixin:
    """Mixin for timestamp fields."""

    @declared_attr
    def created_at(cls):
        return Column(DateTime, default=datetime.utcnow, nullable=False)

    @declared_attr
    def updated_at(cls):
        return Column(
            DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
        )


class AuditMixin(TimestampMixin):
    """Mixin for audit fields."""

    @declared_attr
    def created_by(cls):
        return Column(String(255), nullable=True)

    @declared_attr
    def updated_by(cls):
        return Column(String(255), nullable=True)

    @declared_attr
    def version(cls):
        return Column(Integer, default=1, nullable=False)

    def update_audit_fields(self, user_id: str) -> None:
        """Update audit fields."""
        self.updated_at = datetime.utcnow()
        self.updated_by = user_id
        self.version += 1


class SoftDeleteMixin:
    """Mixin for soft delete functionality."""

    @declared_attr
    def is_deleted(cls):
        return Column(Boolean, default=False, nullable=False)

    @declared_attr
    def deleted_at(cls):
        return Column(DateTime, nullable=True)

    @declared_attr
    def deleted_by(cls):
        return Column(String(255), nullable=True)

    def soft_delete(self, user_id: str) -> None:
        """Soft delete the entity."""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
        self.deleted_by = user_id
        if hasattr(self, "update_audit_fields"):
            self.update_audit_fields(user_id)

    def restore(self, user_id: str) -> None:
        """Restore the entity."""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        if hasattr(self, "update_audit_fields"):
            self.update_audit_fields(user_id)


class BaseModel(Base, AuditMixin):
    """Base model with common fields."""

    __abstract__ = True

    id = Column(Integer, primary_key=True, autoincrement=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            column.name: getattr(self, column.name) for column in self.__table__.columns
        }

    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """Update model from dictionary."""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def __repr__(self) -> str:
        """String representation of the model."""
        return f"<{self.__class__.__name__}(id={self.id})>"


class AuditableModel(BaseModel, SoftDeleteMixin):
    """Model with full audit and soft delete capabilities."""

    __abstract__ = True

    def get_changes(self, original_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get changes from original data."""
        current_data = self.to_dict()
        changes = {}

        for key, value in current_data.items():
            if key not in original_data or original_data[key] != value:
                changes[key] = {"old": original_data.get(key), "new": value}

        return changes


class VersionedModel(AuditableModel):
    """Model with version control."""

    __abstract__ = True

    version_history = Column(Text, nullable=True)  # JSON string of version history

    def create_version_snapshot(self, user_id: str) -> None:
        """Create a version snapshot."""
        import json

        snapshot = {
            "version": self.version,
            "data": self.to_dict(),
            "created_at": datetime.utcnow().isoformat(),
            "created_by": user_id,
        }

        # Parse existing history
        history = []
        if self.version_history:
            try:
                history = json.loads(self.version_history)
            except (json.JSONDecodeError, TypeError):
                history = []

        # Add new snapshot
        history.append(snapshot)

        # Update history
        self.version_history = json.dumps(history)

    def get_version(self, version: int) -> Optional[Dict[str, Any]]:
        """Get entity data for a specific version."""
        import json

        if not self.version_history:
            return None

        try:
            history = json.loads(self.version_history)
            for snapshot in history:
                if snapshot["version"] == version:
                    return snapshot["data"]
        except (json.JSONDecodeError, TypeError):
            pass

        return None

    def rollback_to_version(self, version: int, user_id: str) -> bool:
        """Rollback to a specific version."""
        target_data = self.get_version(version)
        if not target_data:
            return False

        # Restore data from snapshot
        for key, value in target_data.items():
            if key not in ["id", "created_at", "updated_at", "version"]:
                setattr(self, key, value)

        self.version = version
        self.update_audit_fields(user_id)

        return True
