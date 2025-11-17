"""User service implementation."""

import os
from datetime import datetime, timedelta
from typing import List, Optional

import jwt
from passlib.context import CryptContext
from auth_service.core.exceptions import (AuthenticationError,
                                          UserAlreadyExistsError,
                                          UserNotFoundError)
from auth_service.domains.user.repositories.user_repository import \
    UserRepository
from ncm_contracts.auth.schemas import (AuthResponse, LoginRequest,
                                        TokenResponse, UserCreateRequest,
                                        UserResponse, UserUpdateRequest)
from ncm_foundation import get_logger, Settings

logger = get_logger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserService:
    """User service for managing user operations."""
    
    def __init__(self, user_repository: UserRepository, settings: Optional[Settings] = None):
        self.user_repository = user_repository
        self.settings = settings or Settings()
        
        # JWT configuration from environment
        self.jwt_secret = os.getenv("JWT_SECRET")
        if not self.jwt_secret:
            raise ValueError("JWT_SECRET environment variable is required")
        
        self.jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.jwt_expiration_hours = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))
    
    async def create_user(self, request: UserCreateRequest) -> UserResponse:
        """Create a new user."""
        logger.info(f"Creating user with email: {request.email}")
        
        # Check if user already exists
        existing_user = await self.user_repository.get_by_email(request.email)
        if existing_user:
            raise UserAlreadyExistsError(request.email)
        
        # Hash password
        hashed_password = self._hash_password(request.password)
        
        # Create user data
        user_data = {
            "email": request.email,
            "hashed_password": hashed_password,
            "first_name": request.first_name,
            "last_name": request.last_name,
            "organization_id": request.organization_id,
            "role": request.role.value,
            "status": "active",
            "is_active": True,
            "is_superuser": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        user = await self.user_repository.create(user_data)
        return UserResponse.from_orm(user)
    
    async def get_user(self, user_id: int) -> UserResponse:
        """Get user by ID."""
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(user_id)
        return UserResponse.from_orm(user)
    
    async def update_user(self, user_id: int, request: UserUpdateRequest) -> UserResponse:
        """Update user."""
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(user_id)
        
        # Update user data
        update_data = request.dict(exclude_unset=True)
        if update_data:
            update_data["updated_at"] = datetime.utcnow()
            user = await self.user_repository.update(user_id, update_data)
        
        return UserResponse.from_orm(user)
    
    async def list_users(self) -> List[UserResponse]:
        """List all users."""
        users = await self.user_repository.list_all()
        return [UserResponse.from_orm(user) for user in users]
    
    async def authenticate(self, request: LoginRequest) -> AuthResponse:
        """Authenticate user and return auth response."""
        user = await self.user_repository.get_by_email(request.email)
        if not user:
            logger.warning(f"Authentication failed: user not found for email {request.email}")
            raise AuthenticationError("Invalid email or password")
        
        if not self._verify_password(request.password, user.hashed_password):
            logger.warning(f"Authentication failed: invalid password for user {user.id}")
            raise AuthenticationError("Invalid email or password")
        
        if not user.is_active:
            logger.warning(f"Authentication failed: user {user.id} is inactive")
            raise AuthenticationError("User account is inactive")
        
        # Generate JWT token
        token = self._generate_token(user.id, user.email)
        
        logger.info(f"User {user.id} authenticated successfully")
        return AuthResponse(
            user=UserResponse.from_orm(user),
            token=TokenResponse(
                access_token=token,
                token_type="bearer",
                expires_in=self.jwt_expiration_hours * 3600
            )
        )
    
    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        return pwd_context.hash(password)
    
    def _verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify password against hash."""
        return pwd_context.verify(password, hashed_password)
    
    def _generate_token(self, user_id: int, email: str) -> str:
        """Generate JWT token."""
        payload = {
            "user_id": user_id,
            "email": email,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(hours=self.jwt_expiration_hours)
        }
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
