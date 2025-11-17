"""
Entity listeners for audit fields and database events.
"""

import logging
import threading
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import event
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class AuditContext:
    """Thread-local context for audit information."""

    def __init__(self):
        self._local = threading.local()

    def set_user(self, user_id: str) -> None:
        """Set current user for audit."""
        self._local.user_id = user_id

    def get_user(self) -> Optional[str]:
        """Get current user."""
        return getattr(self._local, "user_id", None)

    def clear(self) -> None:
        """Clear audit context."""
        if hasattr(self._local, "user_id"):
            delattr(self._local, "user_id")


# Global audit context
audit_context = AuditContext()


def setup_audit_listeners():
    """Setup SQLAlchemy event listeners for audit fields."""

    @event.listens_for(Session, "before_insert")
    def receive_before_insert(mapper, connection, target):
        """Set audit fields before insert."""
        current_user = audit_context.get_user()

        # Set created_at if not already set
        if hasattr(target, "created_at") and not target.created_at:
            target.created_at = datetime.utcnow()

        # Set updated_at if not already set
        if hasattr(target, "updated_at") and not target.updated_at:
            target.updated_at = datetime.utcnow()

        # Set created_by if not already set
        if hasattr(target, "created_by") and not target.created_by and current_user:
            target.created_by = current_user

        # Set updated_by
        if hasattr(target, "updated_by") and current_user:
            target.updated_by = current_user

        logger.debug(f"Before insert: {target.__class__.__name__} by {current_user}")

    @event.listens_for(Session, "before_update")
    def receive_before_update(mapper, connection, target):
        """Set audit fields before update."""
        current_user = audit_context.get_user()

        # Update timestamp
        if hasattr(target, "updated_at"):
            target.updated_at = datetime.utcnow()

        # Update user
        if hasattr(target, "updated_by") and current_user:
            target.updated_by = current_user

        # Increment version
        if hasattr(target, "version"):
            target.version += 1

        logger.debug(f"Before update: {target.__class__.__name__} by {current_user}")

    @event.listens_for(Session, "before_delete")
    def receive_before_delete(mapper, connection, target):
        """Handle soft delete before hard delete."""
        current_user = audit_context.get_user()

        # Check if entity supports soft delete
        if hasattr(target, "is_deleted") and not target.is_deleted:
            # Convert to soft delete
            target.is_deleted = True
            target.deleted_at = datetime.utcnow()
            if hasattr(target, "deleted_by") and current_user:
                target.deleted_by = current_user

            # Update audit fields
            if hasattr(target, "update_audit_fields") and current_user:
                target.update_audit_fields(current_user)

            logger.debug(f"Soft delete: {target.__class__.__name__} by {current_user}")

            # Prevent actual deletion
            return False

        logger.debug(f"Hard delete: {target.__class__.__name__} by {current_user}")

    @event.listens_for(Session, "after_insert")
    def receive_after_insert(mapper, connection, target):
        """Log after insert."""
        logger.info(
            f"Inserted: {target.__class__.__name__} (id={getattr(target, 'id', 'N/A')})"
        )

    @event.listens_for(Session, "after_update")
    def receive_after_update(mapper, connection, target):
        """Log after update."""
        logger.info(
            f"Updated: {target.__class__.__name__} (id={getattr(target, 'id', 'N/A')})"
        )

    @event.listens_for(Session, "after_delete")
    def receive_after_delete(mapper, connection, target):
        """Log after delete."""
        logger.info(
            f"Deleted: {target.__class__.__name__} (id={getattr(target, 'id', 'N/A')})"
        )


def setup_security_listeners():
    """Setup security-related event listeners."""

    @event.listens_for(Session, "before_insert")
    def log_security_insert(mapper, connection, target):
        """Log security-sensitive insertions."""
        if hasattr(target, "__security_sensitive__") and target.__security_sensitive__:
            logger.warning(f"Security-sensitive insert: {target.__class__.__name__}")

    @event.listens_for(Session, "before_update")
    def log_security_update(mapper, connection, target):
        """Log security-sensitive updates."""
        if hasattr(target, "__security_sensitive__") and target.__security_sensitive__:
            logger.warning(f"Security-sensitive update: {target.__class__.__name__}")


def setup_performance_listeners():
    """Setup performance monitoring listeners."""

    @event.listens_for(Session, "before_bulk_update")
    def log_bulk_update(mapper, connection, target, context):
        """Log bulk update operations."""
        logger.info(f"Bulk update: {target.__class__.__name__}")

    @event.listens_for(Session, "before_bulk_delete")
    def log_bulk_delete(mapper, connection, target, context):
        """Log bulk delete operations."""
        logger.info(f"Bulk delete: {target.__class__.__name__}")


def setup_all_listeners():
    """Setup all database listeners."""
    setup_audit_listeners()
    setup_security_listeners()
    setup_performance_listeners()
    logger.info("All database listeners setup complete")
