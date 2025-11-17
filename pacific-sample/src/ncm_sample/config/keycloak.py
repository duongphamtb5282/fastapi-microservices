"""Keycloak configuration and client setup using ncm-foundation."""

from typing import Optional, Dict, Any
from ncm_foundation.core.security.keycloak import KeycloakManager, KeycloakConfig as FoundationKeycloakConfig
from ncm_sample.config.settings import get_settings


class KeycloakConfig:
    """Keycloak configuration and client management using ncm-foundation."""

    def __init__(self):
        settings = get_settings()

        # Create foundation Keycloak config
        self.foundation_config = FoundationKeycloakConfig(
            server_url=settings.keycloak_server_url,
            realm=settings.keycloak_realm_name,
            client_id=settings.keycloak_client_id,
            client_secret=settings.keycloak_client_secret,
            admin_username=settings.keycloak_admin_username,
            admin_password=settings.keycloak_admin_password,
        )

        # Initialize foundation Keycloak manager
        self.keycloak_manager = KeycloakManager(self.foundation_config)

    async def initialize(self):
        """Initialize Keycloak manager."""
        await self.keycloak_manager.initialize()

    def get_well_known_config(self) -> Optional[dict]:
        """Get Keycloak well-known configuration."""
        try:
            # This would need to be implemented in the foundation KeycloakManager
            # For now, return a basic config
            return {
                "issuer": f"{self.foundation_config.server_url}/realms/{self.foundation_config.realm}",
                "authorization_endpoint": f"{self.foundation_config.server_url}/realms/{self.foundation_config.realm}/protocol/openid-connect/auth",
                "token_endpoint": f"{self.foundation_config.server_url}/realms/{self.foundation_config.realm}/protocol/openid-connect/token",
                "userinfo_endpoint": f"{self.foundation_config.server_url}/realms/{self.foundation_config.realm}/protocol/openid-connect/userinfo",
                "end_session_endpoint": f"{self.foundation_config.server_url}/realms/{self.foundation_config.realm}/protocol/openid-connect/logout",
            }
        except Exception:
            return None

    def get_public_key(self) -> str:
        """Get Keycloak public key for JWT verification."""
        try:
            # This would need to be implemented in the foundation KeycloakManager
            return self.foundation_config.public_key or ""
        except Exception:
            return ""

    async def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with Keycloak."""
        try:
            return await self.keycloak_manager.authenticate_user(username, password)
        except Exception:
            return None

    async def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Get user information from Keycloak."""
        try:
            return await self.keycloak_manager.get_user_info(access_token)
        except Exception:
            return None

    async def refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Refresh access token."""
        try:
            return await self.keycloak_manager.refresh_token(refresh_token)
        except Exception:
            return None


# Global Keycloak config instance
_keycloak_config: Optional[KeycloakConfig] = None


async def get_keycloak_config() -> KeycloakConfig:
    """Get Keycloak configuration instance (async initialization)."""
    global _keycloak_config
    if _keycloak_config is None:
        _keycloak_config = KeycloakConfig()
        await _keycloak_config.initialize()
    return _keycloak_config


def get_keycloak_config_sync() -> KeycloakConfig:
    """Get Keycloak configuration instance (sync for compatibility)."""
    # For backward compatibility, return a non-initialized instance
    # The actual initialization should happen in the lifespan
    return KeycloakConfig()
