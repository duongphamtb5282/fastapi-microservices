"""User repository implementation."""

from typing import List, Optional
from ncm_foundation.core.database.manager import DatabaseManager
from sqlalchemy.ext.asyncio import AsyncSession
from ncm_foundation.core.database import SQLAlchemyRepository
from ncm_sample.features.user_management.models.user import User
from ncm_sample.core.decorators import cache_result


class UserRepository(SQLAlchemyRepository[User]):
    """User repository with SQLAlchemy implementation."""

    def __init__(self, session, cache_manager=None):
        super().__init__(User, session)
        self.cache_manager = cache_manager

    @cache_result(ttl=300, key_prefix="user_repo")
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email with caching."""
        return await self.get_by_field("email", email)

    @cache_result(ttl=300, key_prefix="user_repo")
    async def get_by_id(self, id: int) -> Optional[User]:
        """Get user by ID with caching."""
        return await self.get_by_field("id", id)

    @cache_result(ttl=300, key_prefix="user_repo")
    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username with caching."""
        return await self.get_by_field("username", username)

    @cache_result(ttl=180, key_prefix="user_repo")  # Shorter TTL for lists
    async def get_active_users(self, limit: int = 100, offset: int = 0) -> List[User]:
        """Get active users with caching."""
        return await self.list({"is_active": True}, limit=limit, offset=offset)

    @cache_result(ttl=180, key_prefix="user_repo")  # Shorter TTL for search results
    async def search_users(self, search_term: str, limit: int = 100, offset: int = 0) -> List[User]:
        """Search users by username, email, or name with caching."""
        return await self.search(
            query=search_term,
            fields=["username", "email", "first_name", "last_name"],
            limit=limit,
            offset=offset
        )
