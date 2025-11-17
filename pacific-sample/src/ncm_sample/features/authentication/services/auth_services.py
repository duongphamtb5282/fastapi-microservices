"""
Authentication Services for NCM Sample Project.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from ncm_foundation import DatabaseManager, get_logger
from ncm_foundation.core.database import SecurityAuditLogger
from ncm_sample.config import settings
from ncm_sample.core.decorators import with_session_transaction
from ncm_sample.features.user_management.models.user import User
from passlib.context import CryptContext

logger = get_logger(__name__)
audit_logger = SecurityAuditLogger()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


from ncm_sample.features.shared.services.base_service import DatabaseService

class AuthService(DatabaseService):
    """Authentication service with JWT and password management."""

    def __init__(self, db_manager=None, cache_manager=None):
        super().__init__(db_manager, cache_manager)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password."""
        return pwd_context.verify(plain_password, hashed_password)

    def create_access_token(
        self, data: dict, expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm
        )
        return encoded_jwt

    async def authenticate_user(self, username: str, password: str, ip_address: Optional[str] = None, user_agent: Optional[str] = None, session=None) -> Optional[User]:
        """Authenticate user using user management service."""
        # Import here to avoid circular imports
        from ncm_sample.features.user_management.services import UserService
        from ncm_sample.features.authentication.repositories import AuthAuditLogRepository

        # Create user service with the session if provided
        if session is not None:
            user_service = UserService(session=session, cache_manager=self.cache_manager)
        else:
            user_service = UserService(db_manager=self.db_manager, cache_manager=self.cache_manager)
        user = await user_service.get_user_by_email(username)

        success = False
        if user and self.verify_password(password, user.password_hash):
            success = True

        # Log authentication attempt
        try:
            if session is None:
                session = await self.db_manager.get_session()
            audit_repo = AuthAuditLogRepository(session)
            await audit_repo.log_event(
                user_id=user.id if success else None,
                username=username,
                event_type="login_attempt",
                success=success,
                ip_address=ip_address,
                user_agent=user_agent,
                failure_reason="Invalid credentials" if not success else None
            )
        except Exception as e:
            logger.warning(f"Failed to log authentication audit: {e}")

        if not success:
            return None

        return user

    def create_refresh_token(
        self, data: dict, expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create refresh token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            # Default refresh token expires in 7 days
            expire = datetime.utcnow() + timedelta(days=settings.jwt_refresh_expire_days)

        to_encode.update({
            "exp": expire,
            "type": "refresh",
            "iat": datetime.utcnow()
        })
        encoded_jwt = jwt.encode(
            to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm
        )
        return encoded_jwt

    def verify_refresh_token(self, token: str) -> Optional[dict]:
        """Verify refresh token and return payload."""
        try:
            payload = jwt.decode(
                token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
            )
            if payload.get("type") != "refresh":
                return None
            return payload
        except JWTError:
            return None

    async def refresh_access_token(self, refresh_token: str, correlation_id: Optional[str] = None) -> Optional[dict]:
        """Refresh access token using refresh token."""
        # Verify refresh token
        payload = self.verify_refresh_token(refresh_token)
        if not payload:
            # Log failed refresh attempt (simplified for controller usage)
            logger.warning(f"Invalid refresh token attempt, correlation_id: {correlation_id}")
            return None

        # Get user from payload
        from ncm_sample.features.user_management.services import UserService
        user_service = UserService(db_manager=self.db_manager, cache_manager=self.cache_manager)
        user = await user_service.get_user_by_id(payload.get("user_id"))

        if not user:
            # Log failed refresh attempt due to user not found (simplified for controller usage)
            logger.warning(f"Refresh token for non-existent user: {payload.get('user_id')}, correlation_id: {correlation_id}")
            return None

        # Log successful refresh (simplified for controller usage)
        logger.info(f"Token refreshed for user: {user.username}, correlation_id: {correlation_id}")

        # Create new access token
        access_token_expires = timedelta(minutes=settings.jwt_expire_minutes)
        access_token = self.create_access_token(
            data={"sub": user.username, "user_id": user.id},
            expires_delta=access_token_expires,
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.jwt_expire_minutes * 60,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
            },
        }

    async def login(self, username: str, password: str, correlation_id: Optional[str] = None, session=None) -> Optional[dict]:
        """Login user and return tokens."""
        # For audit logging, we'll use placeholder values since we don't have IP/user agent in this context
        if session is not None:
            async with session.begin():
                user = await self.authenticate_user(username, password, None, None, session=session)
        else:
            user = await self.authenticate_user(username, password, None, None, session=session)
        if not user:
            return None

        access_token_expires = timedelta(minutes=settings.jwt_expire_minutes)
        access_token = self.create_access_token(
            data={"sub": user.username, "user_id": user.id},
            expires_delta=access_token_expires,
        )

        # Create refresh token
        refresh_token = self.create_refresh_token(
            data={"sub": user.username, "user_id": user.id}
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.jwt_expire_minutes * 60,
            "refresh_expires_in": settings.jwt_refresh_expire_days * 24 * 3600,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
            },
        }
