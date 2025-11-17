"""Authentication audit log repository."""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from ncm_foundation.core.database import SQLAlchemyRepository
from ncm_sample.features.authentication.models import AuthAuditLog

class AuthAuditLogRepository(SQLAlchemyRepository[AuthAuditLog]):
    """Repository for authentication audit log operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(AuthAuditLog, session)

    async def log_event(
        self,
        user_id: Optional[int],
        username: Optional[str],
        event_type: str,
        success: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        device_info: Optional[str] = None,
        location: Optional[str] = None,
        failure_reason: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> AuthAuditLog:
        """Log an authentication event."""
        import json

        log_data = {
            "user_id": user_id,
            "username": username,
            "event_type": event_type,
            "success": success,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "device_info": device_info,
            "location": location,
            "failure_reason": failure_reason,
            "session_id": session_id,
            "metadata": json.dumps(metadata) if metadata else None
        }
        return await self.create(log_data)

    async def get_logs_by_user(
        self,
        user_id: int,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuthAuditLog]:
        """Get audit logs for a specific user."""
        filters = {"user_id": user_id}
        return await self.list(
            filters=filters,
            limit=limit,
            offset=offset,
            order_by="created_at"
        )

    async def get_logs_by_username(
        self,
        username: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuthAuditLog]:
        """Get audit logs for a specific username (including failed attempts)."""
        filters = {"username": username}
        return await self.list(
            filters=filters,
            limit=limit,
            offset=offset,
            order_by="created_at"
        )

    async def get_failed_login_attempts(
        self,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        limit: int = 50
    ) -> List[AuthAuditLog]:
        """Get failed login attempts."""
        filters = {
            "event_type": "login_attempt",
            "success": False
        }
        if username:
            filters["username"] = username
        if ip_address:
            filters["ip_address"] = ip_address

        return await self.list(
            filters=filters,
            limit=limit,
            order_by="created_at"
        )

    async def get_recent_activity(
        self,
        user_id: Optional[int] = None,
        limit: int = 50
    ) -> List[AuthAuditLog]:
        """Get recent authentication activity."""
        filters = {
            "event_type": ["login_attempt", "logout", "token_refresh"]
        }
        if user_id:
            filters["user_id"] = user_id

        return await self.list(
            filters=filters,
            limit=limit,
            order_by="created_at"
        )

    async def cleanup_old_logs(self, days_to_keep: int = 90) -> int:
        """Remove audit logs older than specified days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        old_logs = await self.list(filters={"created_at": {"$lt": cutoff_date}})
        for log in old_logs:
            await self.delete(log.id)
        return len(old_logs)
