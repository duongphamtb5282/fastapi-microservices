"""User service implementation."""

from typing import List, Optional
from ncm_sample.features.user_management.models.user import User
from ncm_sample.features.user_management.repositories.user_repository import UserRepository
from ncm_sample.features.user_management.schemas.user import UserCreate, UserUpdate
from ncm_sample.features.shared.services.base_service import BaseService
from ncm_sample.core.decorators import log_method_call, cache_result, with_session_transaction
from ncm_sample.core.security import get_password_hash, verify_password
from ncm_foundation.core.logging import get_logger
from datetime import datetime


class UserService(BaseService[User, UserRepository]):
    """User service with business logic."""

    def __init__(self, repository: UserRepository = None, session=None, cache_manager=None):
        # Use repository if provided, otherwise let BaseService create it
        super().__init__(repository=repository,
                         repository_class=UserRepository if repository is None else None,
                         session=session, cache_manager=cache_manager)
        # Store cache_manager for invalidation
        self.cache_manager = cache_manager

    @log_method_call
    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        # Check if user already exists
        existing_user = await self.repository.get_by_email(user_data.email)
        if existing_user:
            raise ValueError("User with this email already exists")

        existing_username = await self.repository.get_by_username(user_data.username)
        if existing_username:
            raise ValueError("User with this username already exists")

        # Create user
        user_data_dict = {
            "username": user_data.username,
            "email": user_data.email,
            "first_name": user_data.first_name,
            "last_name": user_data.last_name,
            "hashed_password": get_password_hash(user_data.password),
            "is_active": user_data.is_active,
            "is_verified": user_data.is_verified
        }

        user = await self.repository.create(user_data_dict)

        # Invalidate cache for related queries
        if self.cache_manager:
            try:
                # Invalidate user list caches
                await self.cache_manager.invalidate_pattern("user_repo:get_active_users:*")
                await self.cache_manager.invalidate_pattern("user_repo:search_users:*")
                await self.cache_manager.invalidate_pattern("user_repo:list:*")
                await self.cache_manager.invalidate_pattern("user_repo:count_users:*")
            except Exception as e:
                logger = get_logger(__name__)
                logger.warning(f"Failed to invalidate cache after user creation: {e}")

        return user

    @cache_result(ttl=300, key_prefix="user_service")
    @log_method_call
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email with caching."""
        return await self.repository.get_by_email(email)

    # @with_transaction
    @log_method_call
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return await self.repository.get_by_id(user_id)

    @log_method_call
    async def update_user(self, user_id: int, user_data: UserUpdate) -> Optional[User]:
        """Update user."""
        user = await self.repository.get_by_id(user_id)
        if not user:
            return None

        # Update fields
        update_data = user_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)

        user.updated_at = datetime.utcnow()
        update_data = {
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "hashed_password": user.hashed_password,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "last_login": user.last_login,
            "updated_at": user.updated_at
        }

        updated_user = await self.repository.update(user.id, update_data)

        # Invalidate cache for this user and related queries
        if self.cache_manager:
            try:
                # Invalidate specific user caches
                await self.cache_manager.invalidate_pattern(f"user_repo:get_by_id:{user_id}")
                await self.cache_manager.invalidate_pattern(f"user_repo:get_by_email:{user.email}")
                await self.cache_manager.invalidate_pattern(f"user_repo:get_by_username:{user.username}")
                # Invalidate list and search caches
                await self.cache_manager.invalidate_pattern("user_repo:get_active_users:*")
                await self.cache_manager.invalidate_pattern("user_repo:search_users:*")
                await self.cache_manager.invalidate_pattern("user_repo:list:*")
                await self.cache_manager.invalidate_pattern("user_repo:count_users:*")
            except Exception as e:
                logger = get_logger(__name__)
                logger.warning(f"Failed to invalidate cache after user update: {e}")

        return updated_user

    @log_method_call
    async def delete_user(self, user_id: int) -> bool:
        """Delete user."""
        # Get user info before deletion for cache invalidation
        user = await self.repository.get_by_id(user_id)
        if not user:
            return False

        success = await self.repository.delete(user_id)

        if success and self.cache_manager:
            try:
                # Invalidate specific user caches
                await self.cache_manager.invalidate_pattern(f"user_repo:get_by_id:{user_id}")
                await self.cache_manager.invalidate_pattern(f"user_repo:get_by_email:{user.email}")
                await self.cache_manager.invalidate_pattern(f"user_repo:get_by_username:{user.username}")
                # Invalidate list and search caches
                await self.cache_manager.invalidate_pattern("user_repo:get_active_users:*")
                await self.cache_manager.invalidate_pattern("user_repo:search_users:*")
                await self.cache_manager.invalidate_pattern("user_repo:list:*")
                await self.cache_manager.invalidate_pattern("user_repo:count_users:*")
            except Exception as e:
                logger = get_logger(__name__)
                logger.warning(f"Failed to invalidate cache after user deletion: {e}")

        return success

    @log_method_call
    async def list_users(self, skip: int = 0, limit: int = 100,
                         filters: dict = None) -> List[User]:
        """List users with pagination and filters."""
        return await self.repository.list(filters=filters, limit=limit, offset=skip)

    @log_method_call
    async def count_users(self, filters: dict = None) -> int:
        """Count users with optional filters."""
        return await self.repository.count(filters=filters)

    @log_method_call
    async def verify_user_password(self, email: str, password: str) -> Optional[User]:
        """Verify user password and return user if valid."""
        user = await self.repository.get_by_email(email)
        if user and verify_password(password, user.hashed_password):
            # Update last login
            user.last_login = datetime.utcnow()
            await self.repository.update(user.id, {"last_login": datetime.utcnow()})
            return user
        return None

    @log_method_call
    async def change_password(self, user_id: int, current_password: str, new_password: str) -> bool:
        """Change user password."""
        user = await self.repository.get_by_id(user_id)
        if not user:
            return False

        if not verify_password(current_password, user.hashed_password):
            return False

        # Update password and timestamp
        update_data = {
            "hashed_password": get_password_hash(new_password),
            "updated_at": datetime.utcnow()
        }
        await self.repository.update(user_id, update_data)

        # Invalidate cache for this user
        if self.cache_manager:
            try:
                await self.cache_manager.invalidate_pattern(f"user_repo:get_by_id:{user_id}")
                await self.cache_manager.invalidate_pattern(f"user_repo:get_by_email:{user.email}")
                await self.cache_manager.invalidate_pattern(f"user_repo:get_by_username:{user.username}")
            except Exception as e:
                logger = get_logger(__name__)
                logger.warning(f"Failed to invalidate cache after password change: {e}")

        return True

    @log_method_call
    async def activate_user(self, user_id: int) -> bool:
        """Activate user account."""
        user = await self.repository.get_by_id(user_id)
        if not user:
            return False

        # Update active status and timestamp
        update_data = {
            "is_active": True,
            "updated_at": datetime.utcnow()
        }
        await self.repository.update(user_id, update_data)

        # Invalidate cache for this user and active user lists
        if self.cache_manager:
            try:
                await self.cache_manager.invalidate_pattern(f"user_repo:get_by_id:{user_id}")
                await self.cache_manager.invalidate_pattern("user_repo:get_active_users:*")
            except Exception as e:
                logger = get_logger(__name__)
                logger.warning(f"Failed to invalidate cache after user activation: {e}")

        return True

    @log_method_call
    async def deactivate_user(self, user_id: int) -> bool:
        """Deactivate user account."""
        user = await self.repository.get_by_id(user_id)
        if not user:
            return False

        # Update active status and timestamp
        update_data = {
            "is_active": False,
            "updated_at": datetime.utcnow()
        }
        await self.repository.update(user_id, update_data)

        # Invalidate cache for this user and active user lists
        if self.cache_manager:
            try:
                await self.cache_manager.invalidate_pattern(f"user_repo:get_by_id:{user_id}")
                await self.cache_manager.invalidate_pattern("user_repo:get_active_users:*")
            except Exception as e:
                logger = get_logger(__name__)
                logger.warning(f"Failed to invalidate cache after user deactivation: {e}")

        return True

    @log_method_call
    async def get_active_users(self, limit: int = 100, offset: int = 0) -> List[User]:
        """Get active users."""
        return await self.repository.get_active_users(limit=limit, offset=offset)
