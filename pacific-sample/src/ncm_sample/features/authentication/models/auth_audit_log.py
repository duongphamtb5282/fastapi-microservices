"""Authentication audit log model."""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean
from ncm_foundation.core.database.models import BaseModel

class AuthAuditLog(BaseModel):
    """Authentication audit log for tracking auth events."""

    __tablename__ = "auth_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Nullable for failed attempts
    username = Column(String(255), nullable=True)  # Store username for failed attempts
    event_type = Column(String(100), nullable=False)  # login, logout, token_refresh, etc.
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    device_info = Column(String(500), nullable=True)
    location = Column(String(255), nullable=True)
    success = Column(Boolean, nullable=False)
    failure_reason = Column(Text, nullable=True)  # Reason for failure
    session_id = Column(String(255), nullable=True)  # Link to session if available
    metadata_json = Column(Text, nullable=True)  # JSON metadata for additional info

    @classmethod
    def log_login_attempt(
        cls,
        username: str,
        success: bool,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        failure_reason: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> "AuthAuditLog":
        """Create a login attempt audit log entry."""
        return cls(
            user_id=user_id,
            username=username,
            event_type="login_attempt",
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            failure_reason=failure_reason,
            session_id=session_id
        )

    @classmethod
    def log_logout(
        cls,
        user_id: int,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> "AuthAuditLog":
        """Create a logout audit log entry."""
        return cls(
            user_id=user_id,
            event_type="logout",
            ip_address=ip_address,
            user_agent=user_agent,
            success=True,
            session_id=session_id
        )

    @classmethod
    def log_token_refresh(
        cls,
        user_id: int,
        success: bool,
        ip_address: Optional[str] = None,
        failure_reason: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> "AuthAuditLog":
        """Create a token refresh audit log entry."""
        return cls(
            user_id=user_id,
            event_type="token_refresh",
            ip_address=ip_address,
            success=success,
            failure_reason=failure_reason,
            session_id=session_id
        )

    def __repr__(self) -> str:
        return f"<AuthAuditLog(id={self.id}, user_id={self.user_id}, event_type='{self.event_type}', success={self.success})>"
