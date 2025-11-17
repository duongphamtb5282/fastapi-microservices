"""User session model for authentication."""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from ncm_foundation.core.database.models import BaseModel

class UserSession(BaseModel):
    """User session model for tracking active user sessions."""

    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    device_info = Column(String(500), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    location = Column(String(255), nullable=True)  # City/Country info
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_activity = Column(DateTime, nullable=False, default=datetime.utcnow)
    login_time = Column(DateTime, nullable=False, default=datetime.utcnow)

    def is_expired(self) -> bool:
        """Check if session is expired."""
        return datetime.utcnow() > self.expires_at

    def is_valid(self) -> bool:
        """Check if session is valid (not expired and active)."""
        return self.is_active and not self.is_expired()

    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.utcnow()

    def deactivate(self) -> None:
        """Deactivate the session."""
        self.is_active = False

    def __repr__(self) -> str:
        return f"<UserSession(id={self.id}, user_id={self.user_id}, is_active={self.is_active})>"
