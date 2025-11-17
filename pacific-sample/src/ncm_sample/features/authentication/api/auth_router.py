"""
Authentication API Router
"""

from fastapi import APIRouter
from ncm_sample.core.container import get_container, get_provider
from ncm_sample.features.authentication.controllers import AuthController
from ncm_sample.features.authentication.services import AuthService
from ncm_foundation.core.database.manager import DatabaseManager

# Create router instance
router = APIRouter(prefix="/auth", tags=["Authentication"])

AUTH_SVC_KEY = "auth_service"


def init_feature(auth_svc: AuthService = None) -> APIRouter:
    """Initialize authentication feature with controller.

    Returns the configured router. This allows the main application to
    call feature-level initialization during startup.
    """
    if auth_svc is None:
        container = get_container()
        db_manager = container.get(DatabaseManager)
        auth_svc = AuthService(db_manager=db_manager, cache_manager=None)  # CacheManager not available

    # Register service in container for DI
    container.register_singleton(AUTH_SVC_KEY, auth_svc)

    # Create controller and get its router
    controller = AuthController(auth_svc)
    controller_router = controller.get_router()

    # Include controller routes in our router
    router.include_router(controller_router)

    return router
