"""FastAPI dependencies for dependency injection."""

from typing import Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from ncm_sample.core.container import get_container
from ncm_foundation.core.cache import CacheManager
from ncm_foundation.core.database.manager import DatabaseManager
from ncm_foundation.core.logging import LogManager
# from ncm_foundation.core.cache import CacheManager
from ncm_sample.config.settings import Settings, get_settings
from ncm_sample.config.keycloak import KeycloakConfig, get_keycloak_config
from sqlalchemy.ext.asyncio import AsyncSession

# Security scheme
security = HTTPBearer()

# Dependency functions


def get_settings_dependency() -> Settings:
    """Get application settings."""
    return get_settings()


def get_database_manager() -> DatabaseManager:
    """Get database manager from DI container."""
    container = get_container()
    return container.get(DatabaseManager)


def get_log_manager() -> LogManager:
    """Get log manager from DI container."""
    container = get_container()
    return container.get(LogManager)


def get_cache_manager() -> CacheManager:
    container = get_container()
    return container.get(CacheManager)


def get_keycloak_config_dependency() -> KeycloakConfig:
    """Get Keycloak configuration."""
    return get_keycloak_config()


async def get_session_db() -> AsyncSession:  # type: ignore
    """Get database session dependency."""
    db_manager = get_database_manager()
    async with db_manager.get_session_context() as session:
        yield session


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    keycloak_config: KeycloakConfig = Depends(get_keycloak_config_dependency)
) -> dict:
    """Get current authenticated user from JWT token."""
    try:
        # Check if Keycloak is available
        if keycloak_config.openid_client is None:
            # For development/testing, create a mock user
            return {
                'sub': 'test-user-id',
                'username': 'testuser',
                'email': 'test@example.com',
                'roles': ['user'],
                'client_roles': ['user:read', 'user:create']
            }

        # Verify token with Keycloak
        token_info = keycloak_config.openid_client.introspect(
            credentials.credentials)

        if not token_info.get('active', False):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

        return {
            'sub': token_info.get('sub'),
            'username': token_info.get('preferred_username'),
            'email': token_info.get('email'),
            'roles': token_info.get('realm_access', {}).get('roles', []),
            'client_roles': token_info.get('resource_access', {}).get(keycloak_config.settings.keycloak_client_id, {}).get('roles', [])
        }

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication error: {str(e)}"
        )


def require_permissions(required_permissions: List[str]):
    """Create a dependency function that requires specific permissions."""
    def permission_dependency(current_user: dict = Depends(get_current_user)) -> dict:
        user_permissions = current_user.get('client_roles', [])

        if not any(permission in user_permissions for permission in required_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )

        return current_user

    return permission_dependency
