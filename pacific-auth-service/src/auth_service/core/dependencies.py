"""Dependency injection for auth service."""

from auth_service.domains.user.repositories.user_repository import \
    UserRepository
from auth_service.domains.user.services.user_service import UserService
from fastapi import Depends
from ncm_foundation import CacheManager, DatabaseManager, Settings
from sqlalchemy.orm import Session

# Global instances
_settings = Settings()
db_manager = DatabaseManager(_settings)
cache_manager = CacheManager(_settings)


def get_settings() -> Settings:
    """Get settings dependency."""
    return _settings


async def get_db_session() -> Session:
    """Get database session dependency."""
    async with db_manager.get_read_session() as session:
        yield session


async def get_user_repository(db_session: Session = Depends(get_db_session)) -> UserRepository:
    """Get user repository dependency."""
    return UserRepository(db_session)


async def get_user_service(
    user_repository: UserRepository = Depends(get_user_repository),
    settings: Settings = Depends(get_settings)
) -> UserService:
    """Get user service dependency."""
    return UserService(user_repository, settings)


# TODO: Implement organization domain
# async def get_organization_repository(db_session: Session = Depends(get_db_session)) -> OrganizationRepository:
#     """Get organization repository dependency."""
#     return OrganizationRepository(db_session)
#
#
# async def get_organization_service(org_repository: OrganizationRepository = Depends(get_organization_repository)) -> OrganizationService:
#     """Get organization service dependency."""
#     return OrganizationService(org_repository)
