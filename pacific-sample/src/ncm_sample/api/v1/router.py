"""API v1 router configuration."""

from fastapi import APIRouter
from ncm_foundation.core.database.manager import DatabaseManager
from ncm_foundation.core.cache.manager import CacheManager
from ncm_sample.features.user_management.controllers.user_controller import UserController
from ncm_sample.features.user_management.services.user_service import UserService
from ncm_sample.features.user_management.repositories.user_repository import UserRepository

def create_v1_router(db_manager: DatabaseManager) -> APIRouter:
    """Create API v1 router with all endpoints."""
    router = APIRouter(prefix="/api/v1")

    # Register services in DI container
    from ncm_sample.core.container import get_container
    from ncm_foundation.core.cache.manager import CacheManager

    container = get_container()

    # Register database manager instance
    container.register_instance(DatabaseManager, db_manager)

    # Register cache manager (if not already registered)
    if not container.is_registered(CacheManager):
        try:
            cache_manager = CacheManager()
            container.register_singleton(CacheManager, cache_manager)
        except Exception:
            # CacheManager not available, will fall back to no caching
            pass

    # Initialize controllers with service classes
    user_controller = UserController()

    # Include controller routers
    router.include_router(user_controller.router)

    return router
