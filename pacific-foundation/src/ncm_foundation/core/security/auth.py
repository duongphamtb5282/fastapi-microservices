"""
Authentication and authorization components.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from ncm_foundation.core.logging import logger


class User(BaseModel):
    """User model for authentication."""

    id: str
    username: str
    email: str
    roles: list[str] = []
    is_active: bool = True


class AuthManager:
    """Manages authentication and authorization."""

    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        logger.info("AuthManager initialized")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return self.password_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Hash a password."""
        return self.password_context.hash(password)

    def create_access_token(
        self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.JWTError as e:
            logger.error(f"JWT error: {e}")
            return None


class JWTManager:
    """JWT token management."""

    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
        logger.info("JWTManager initialized")

    def create_token(
        self, user: User, expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a JWT token for a user."""
        data = {
            "sub": user.id,
            "username": user.username,
            "email": user.email,
            "roles": user.roles,
            "is_active": user.is_active,
        }
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=24)
        data.update({"exp": expire})
        return jwt.encode(data, self.secret_key, algorithm=self.algorithm)

    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode a JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.JWTError as e:
            logger.error(f"JWT decode error: {e}")
            return None


class PasswordManager:
    """Password management utilities."""

    def __init__(self):
        self.password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        logger.info("PasswordManager initialized")

    def hash_password(self, password: str) -> str:
        """Hash a password."""
        return self.password_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return self.password_context.verify(plain_password, hashed_password)

    def check_password_strength(self, password: str) -> Dict[str, Any]:
        """Check password strength."""
        score = 0
        feedback = []

        if len(password) >= 8:
            score += 1
        else:
            feedback.append("Password should be at least 8 characters long")

        if any(c.isupper() for c in password):
            score += 1
        else:
            feedback.append("Password should contain uppercase letters")

        if any(c.islower() for c in password):
            score += 1
        else:
            feedback.append("Password should contain lowercase letters")

        if any(c.isdigit() for c in password):
            score += 1
        else:
            feedback.append("Password should contain numbers")

        if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            score += 1
        else:
            feedback.append("Password should contain special characters")

        return {
            "score": score,
            "max_score": 5,
            "feedback": feedback,
            "is_strong": score >= 4,
        }
