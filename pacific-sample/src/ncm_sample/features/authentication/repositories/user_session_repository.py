"""User session repository."""

from typing import Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from ncm_foundation.core.database import DatabaseManager, SQLAlchemyRepository
from ncm_sample.features.authentication.models import UserSession

class UserSessionRepository(SQLAlchemyRepository[UserSession]):
    """Repository for user session operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(UserSession, session)

    async def create_session(
        self,
        user_id: int,
        session_token: str,
        expires_at: datetime,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        location: Optional[str] = None
    ) -> UserSession:
        """Create a new user session."""
        session_data = {
            "user_id": user_id,
            "session_token": session_token,
            "expires_at": expires_at,
            "device_info": device_info,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "location": location
        }
        return await self.create(session_data)

    async def get_by_token(self, session_token: str) -> Optional[UserSession]:
        """Get session by session token."""
        return await self.get_by_field("session_token", session_token)

    async def get_active_sessions_by_user(self, user_id: int) -> List[UserSession]:
        """Get all active sessions for a user."""
        filters = {
            "user_id": user_id,
            "is_active": True,
            "expires_at": {"$gt": datetime.utcnow()}
        }
        return await self.list(filters=filters)

    async def get_session_by_id(self, session_id: int) -> Optional[UserSession]:
        """Get session by ID."""
        return await self.get_by_id(session_id)

    async def update_activity(self, session_token: str) -> bool:
        """Update last activity for a session."""
        session = await self.get_by_field("session_token", session_token)
        if session:
            session.update_activity()
            await self.update(session.id, {"last_activity": session.last_activity})
            return True
        return False

    async def deactivate_session(self, session_id: int) -> bool:
        """Deactivate a session."""
        session = await self.get_by_id(session_id)
        if session:
            await self.update(session_id, {"is_active": False})
            return True
        return False

    async def deactivate_all_user_sessions(self, user_id: int) -> int:
        """Deactivate all sessions for a user."""
        active_sessions = await self.get_active_sessions_by_user(user_id)
        for session in active_sessions:
            await self.update(session.id, {"is_active": False})
        return len(active_sessions)

    async def cleanup_expired_sessions(self) -> int:
        """Remove all expired sessions."""
        expired_sessions = await self.list(filters={"expires_at": {"$lte": datetime.utcnow()}})
        for session in expired_sessions:
            await self.delete(session.id)
        return len(expired_sessions)
