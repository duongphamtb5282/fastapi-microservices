"""Security utilities and middleware."""

from typing import List, Optional
from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from ncm_sample.config.settings import Settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)

def create_access_token(data: dict, settings: Settings) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)

def verify_token(token: str, settings: Settings) -> Optional[dict]:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError:
        return None

def check_permissions(user_roles: List[str], required_permissions: List[str]) -> bool:
    """Check if user has required permissions."""
    return any(permission in user_roles for permission in required_permissions)

def require_roles(required_roles: List[str]):
    """Decorator to require specific roles."""
    def role_checker(user_roles: List[str]):
        if not any(role in user_roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role permissions"
            )
        return True
    
    return role_checker

def mask_sensitive_data(data: dict, sensitive_fields: List[str] = None) -> dict:
    """Mask sensitive data in a dictionary."""
    if sensitive_fields is None:
        sensitive_fields = ['password', 'secret', 'token', 'key', 'ssn', 'credit_card']
    
    masked_data = data.copy()
    
    for field in sensitive_fields:
        if field in masked_data:
            masked_data[field] = "***"
    
    return masked_data
