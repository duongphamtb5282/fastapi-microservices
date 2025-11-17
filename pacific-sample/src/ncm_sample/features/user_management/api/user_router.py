"""
User Management API Router
"""

import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from ncm_foundation.core.logging.manager import (correlation_id_var,
                                                 request_id_var, user_id_var)
from ncm_sample.api import get_current_user  # Import from main API file
from ncm_sample.config import settings
from ncm_sample.core.container import get_container, get_provider
from ncm_sample.features.messaging.services import NotificationService
from ncm_sample.features.user_management.schemas import (HealthResponse,
                                                         RoleCreate,
                                                         RoleResponse,
                                                         RoleUpdate,
                                                         UserCreate,
                                                         UserResponse,
                                                         UserRoleCreate,
                                                         UserRoleResponse,
                                                         UserUpdate,
                                                         UserWithRoles)
from ncm_sample.features.user_management.services import (RoleService,
                                                          UserRoleService,
                                                          UserService)

# Import global services (these would be dependency injected in a real app)
logger = logging.getLogger(__name__)
DB_KEY = "db_manager"
CACHE_KEY = "cache_manager"
USER_SVC_KEY = "user_service"
ROLE_SVC_KEY = "role_service"
USER_ROLE_SVC_KEY = "user_role_service"
NOTIF_SVC_KEY = "notification_service"

# module no longer holds service globals; services are resolved via DI

router = APIRouter(prefix="/users", tags=["User Management"])


def init_feature(
    db_mgr,
    cache_mgr,
    user_svc: UserService = None,
    role_svc: RoleService = None,
    user_role_svc: UserRoleService = None,
    notification_svc: NotificationService = None,
):
    """Initialize module-level services for the user management feature.

    This function is intended to be called from the application's startup
    handler so that routers remain self-contained and the main app can
    delegate feature initialization to the feature package.
    """
    # Register managers and services into the container so route handlers can
    # resolve them via FastAPI dependencies.
    container.register_singleton(DB_KEY, db_mgr)
    container.register_singleton(CACHE_KEY, cache_mgr)

    # create or use provided services
    real_user_svc = user_svc or UserService(db_mgr, cache_mgr)
    real_role_svc = role_svc or RoleService(db_mgr, cache_mgr)
    real_user_role_svc = user_role_svc or UserRoleService(db_mgr, cache_mgr)

    container.register_singleton(USER_SVC_KEY, real_user_svc)
    container.register_singleton(ROLE_SVC_KEY, real_role_svc)
    container.register_singleton(USER_ROLE_SVC_KEY, real_user_role_svc)
    container.register_singleton(NOTIF_SVC_KEY, notification_svc)

    return router


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    user_service: UserService = Depends(get_provider(USER_SVC_KEY)),
    notification_service: NotificationService | None = Depends(
        get_provider(NOTIF_SVC_KEY)
    ),
):
    """Create a new user."""
    correlation_id = correlation_id_var.get()

    logger.info(
        f"Creating user: {user_data.email}",
        extra={
            "correlation_id": correlation_id,
            "email": user_data.email,
        },
    )

    try:
        # Check if user already exists
        existing_user = await user_service.get_user_by_email(user_data.email)
        if existing_user:
            logger.warning(
                f"User creation failed - email already exists: {user_data.email}",
                extra={
                    "correlation_id": correlation_id,
                    "existing_user_id": str(existing_user.id),
                },
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists",
            )

        # For demo purposes, create user without specific creator
        user = await user_service.create_user(user_data, "system")

        # Send notification about user creation if messaging is enabled
        if notification_service:
            await notification_service.notify_user_created(user)

        logger.info(
            f"User created successfully",
            extra={
                "correlation_id": correlation_id,
                "new_user_id": str(user.id),
            },
        )

        return UserResponse.from_orm(user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to create user: {str(e)}",
            extra={
                "correlation_id": correlation_id,
                "error_type": type(e).__name__,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user",
        )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int, user_service: UserService = Depends(get_provider(USER_SVC_KEY))
):
    """Get user by ID."""
    correlation_id = correlation_id_var.get()

    logger.info(f"Getting user: {user_id}", extra={"correlation_id": correlation_id})

    user = await user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return UserResponse.from_orm(user)


@router.get("/", response_model=List[UserResponse])
async def list_users(
    limit: int = 100,
    offset: int = 0,
    user_service: UserService = Depends(get_provider(USER_SVC_KEY)),
):
    """List users."""
    correlation_id = correlation_id_var.get()

    logger.info(
        f"Listing users: limit={limit}, offset={offset}",
        extra={"correlation_id": correlation_id},
    )

    users = await user_service.list_users(limit, offset)
    return [UserResponse.from_orm(user) for user in users]


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    user_service: UserService = Depends(get_provider(USER_SVC_KEY)),
):
    """Update user."""
    correlation_id = correlation_id_var.get()

    logger.info(f"Updating user: {user_id}", extra={"correlation_id": correlation_id})

    user = await user_service.update_user(user_id, user_data, "system")
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return UserResponse.from_orm(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int, user_service: UserService = Depends(get_provider(USER_SVC_KEY))
):
    """Delete user."""
    correlation_id = correlation_id_var.get()

    logger.info(f"Deleting user: {user_id}", extra={"correlation_id": correlation_id})

    success = await user_service.delete_user(user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )


# Role endpoints
@router.post(
    "/roles/", response_model=RoleResponse, status_code=status.HTTP_201_CREATED
)
async def create_role(
    role_data: RoleCreate,
    role_service: RoleService = Depends(get_provider(ROLE_SVC_KEY)),
):
    """Create a new role."""
    correlation_id = correlation_id_var.get()

    logger.info(
        f"Creating role: {role_data.name}", extra={"correlation_id": correlation_id}
    )

    role = await role_service.create_role(role_data, "system")
    return RoleResponse.from_orm(role)


@router.get("/roles/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: int, role_service: RoleService = Depends(get_provider(ROLE_SVC_KEY))
):
    """Get role by ID."""
    correlation_id = correlation_id_var.get()

    role = await role_service.get_role_by_id(role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Role not found"
        )

    return RoleResponse.from_orm(role)


@router.get("/roles/", response_model=List[RoleResponse])
async def list_roles(
    limit: int = 100,
    offset: int = 0,
    role_service: RoleService = Depends(get_provider(ROLE_SVC_KEY)),
):
    """List roles."""
    correlation_id = correlation_id_var.get()

    roles = await role_service.list_roles(limit, offset)
    return [RoleResponse.from_orm(role) for role in roles]


# User role endpoints
@router.post(
    "/{user_id}/roles/",
    response_model=UserRoleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def assign_role(
    user_id: int,
    role_data: UserRoleCreate,
    user_role_service: UserRoleService = Depends(get_provider(USER_ROLE_SVC_KEY)),
):
    """Assign role to user."""
    correlation_id = correlation_id_var.get()

    logger.info(
        f"Assigning role {role_data.role_id} to user {user_id}",
        extra={"correlation_id": correlation_id},
    )

    user_role = await user_role_service.assign_role(
        user_id, role_data.role_id, "system"
    )
    return UserRoleResponse.from_orm(user_role)


@router.get("/{user_id}/roles/", response_model=List[RoleResponse])
async def get_user_roles(
    user_id: int,
    user_role_service: UserRoleService = Depends(get_provider(USER_ROLE_SVC_KEY)),
):
    """Get user roles."""
    correlation_id = correlation_id_var.get()

    roles = await user_role_service.get_user_roles(user_id)
    return [RoleResponse.from_orm(role) for role in roles]


# Health check endpoint
@router.get("/health", response_model=HealthResponse)
async def health_check(
    db_manager=Depends(get_provider(DB_KEY)),
    cache_manager=Depends(get_provider(CACHE_KEY)),
):
    """Health check endpoint for user management."""
    correlation_id = correlation_id_var.get()

    try:
        # Check service health
        db_health = await db_manager.health_check() if db_manager else False
        cache_health = await cache_manager.health_check() if cache_manager else False

        services = {
            "database": db_health,
            "cache": cache_health,
            "user_service": True,  # User service is always available if API is running
        }

        overall_status = "healthy" if all(services.values()) else "unhealthy"

        return HealthResponse(
            status=overall_status,
            timestamp=datetime.utcnow(),
            services=services,
            version=settings.app_version,
        )

    except Exception as e:
        logger.error(f"User management health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.utcnow(),
            services={"error": str(e)},
            version=settings.app_version,
        )
