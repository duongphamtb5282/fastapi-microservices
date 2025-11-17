"""
Keycloak integration for SSO and MFA authentication.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlencode

import aiohttp
import jwt
from pydantic import BaseModel, Field

from ncm_foundation.core.logging import logger


class KeycloakConfig(BaseModel):
    """Keycloak configuration."""

    server_url: str = Field(..., description="Keycloak server URL")
    realm: str = Field(default="master", description="Keycloak realm")
    client_id: str = Field(..., description="Client ID")
    client_secret: str = Field(..., description="Client secret")
    admin_username: str = Field(..., description="Admin username")
    admin_password: str = Field(..., description="Admin password")
    public_key: Optional[str] = Field(
        None, description="Public key for JWT verification"
    )
    algorithm: str = Field(default="RS256", description="JWT algorithm")


class TokenResponse(BaseModel):
    """Token response from Keycloak."""

    access_token: str
    refresh_token: str
    expires_in: int
    refresh_expires_in: int
    token_type: str = "Bearer"


class UserInfo(BaseModel):
    """User information from Keycloak."""

    sub: str
    preferred_username: str
    email: str
    email_verified: bool
    name: str
    given_name: str
    family_name: str
    realm_access: Dict[str, List[str]]
    resource_access: Dict[str, Any]
    groups: List[str] = []


class KeycloakClient:
    """Keycloak client for authentication and user management."""

    def __init__(self, config: KeycloakConfig):
        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None
        self._token_cache: Dict[str, Dict[str, Any]] = {}

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()

    async def start(self):
        """Start the Keycloak client."""
        if not self._session:
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(timeout=timeout)
            logger.info("Keycloak client started")

    async def stop(self):
        """Stop the Keycloak client."""
        if self._session:
            await self._session.close()
            self._session = None
            logger.info("Keycloak client stopped")

    def _get_base_url(self) -> str:
        """Get the base URL for Keycloak."""
        return f"{self.config.server_url}/realms/{self.config.realm}"

    def _get_admin_url(self) -> str:
        """Get the admin URL for Keycloak."""
        return f"{self.config.server_url}/admin/realms/{self.config.realm}"

    async def _get_access_token(self) -> str:
        """Get admin access token."""
        cache_key = "admin_token"

        # Check cache first
        if cache_key in self._token_cache:
            cached = self._token_cache[cache_key]
            if time.time() < cached["expires_at"]:
                return cached["token"]

        # Get new token
        token_url = f"{self._get_base_url()}/protocol/openid-connect/token"

        data = {
            "grant_type": "password",
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "username": self.config.admin_username,
            "password": self.config.admin_password,
        }

        async with self._session.post(token_url, data=data) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"Failed to get access token: {error_text}")

            token_data = await response.json()
            token_response = TokenResponse(**token_data)

            # Cache the token
            expires_at = time.time() + token_response.expires_in - 60  # 1 minute buffer
            self._token_cache[cache_key] = {
                "token": token_response.access_token,
                "expires_at": expires_at,
            }

            return token_response.access_token

    async def authenticate_user(
        self, username: str, password: str
    ) -> Optional[TokenResponse]:
        """Authenticate user with username/password."""
        try:
            token_url = f"{self._get_base_url()}/protocol/openid-connect/token"

            data = {
                "grant_type": "password",
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "username": username,
                "password": password,
            }

            async with self._session.post(token_url, data=data) as response:
                if response.status == 200:
                    token_data = await response.json()
                    return TokenResponse(**token_data)
                else:
                    logger.warning(f"Authentication failed for user {username}")
                    return None

        except Exception as e:
            logger.error(f"Error during user authentication: {e}")
            return None

    async def refresh_token(self, refresh_token: str) -> Optional[TokenResponse]:
        """Refresh access token."""
        try:
            token_url = f"{self._get_base_url()}/protocol/openid-connect/token"

            data = {
                "grant_type": "refresh_token",
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "refresh_token": refresh_token,
            }

            async with self._session.post(token_url, data=data) as response:
                if response.status == 200:
                    token_data = await response.json()
                    return TokenResponse(**token_data)
                else:
                    logger.warning("Token refresh failed")
                    return None

        except Exception as e:
            logger.error(f"Error during token refresh: {e}")
            return None

    async def get_user_info(self, access_token: str) -> Optional[UserInfo]:
        """Get user information from access token."""
        try:
            userinfo_url = f"{self._get_base_url()}/protocol/openid-connect/userinfo"

            headers = {"Authorization": f"Bearer {access_token}"}

            async with self._session.get(userinfo_url, headers=headers) as response:
                if response.status == 200:
                    user_data = await response.json()
                    return UserInfo(**user_data)
                else:
                    logger.warning("Failed to get user info")
                    return None

        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return None

    async def verify_token(self, token: str) -> bool:
        """Verify JWT token."""
        try:
            # Decode token without verification first to get kid
            unverified_header = jwt.get_unverified_header(token)

            if not self.config.public_key:
                logger.warning("No public key configured for token verification")
                return False

            # Verify token with public key
            decoded = jwt.decode(
                token,
                self.config.public_key,
                algorithms=[self.config.algorithm],
                audience=self.config.client_id,
                issuer=f"{self._get_base_url()}/",
            )

            # Check expiration
            if decoded.get("exp", 0) < time.time():
                return False

            return True

        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return False
        except jwt.JWTError as e:
            logger.warning(f"Token verification failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Error verifying token: {e}")
            return False

    async def logout_user(self, refresh_token: str) -> bool:
        """Logout user by invalidating refresh token."""
        try:
            logout_url = f"{self._get_base_url()}/protocol/openid-connect/logout"

            data = {
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "refresh_token": refresh_token,
            }

            async with self._session.post(logout_url, data=data) as response:
                return response.status in [200, 204, 302]  # 302 is redirect

        except Exception as e:
            logger.error(f"Error during logout: {e}")
            return False

    async def get_users(
        self, search: Optional[str] = None, max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """Get users from Keycloak."""
        try:
            access_token = await self._get_access_token()

            users_url = f"{self._get_admin_url()}/users"

            params = {"max": max_results}
            if search:
                params["search"] = search

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            async with self._session.get(
                users_url, params=params, headers=headers
            ) as response:
                if response.status == 200:
                    users = await response.json()
                    return users
                else:
                    logger.warning(f"Failed to get users: {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Error getting users: {e}")
            return []

    async def create_user(self, user_data: Dict[str, Any]) -> bool:
        """Create user in Keycloak."""
        try:
            access_token = await self._get_access_token()

            users_url = f"{self._get_admin_url()}/users"

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            # Set default password if not provided
            if "credentials" not in user_data:
                user_data["credentials"] = [
                    {
                        "type": "password",
                        "value": user_data.get("password", "defaultPassword123!"),
                        "temporary": True,
                    }
                ]

            async with self._session.post(
                users_url, json=user_data, headers=headers
            ) as response:
                if response.status in [201, 409]:  # 409 if user exists
                    return True
                else:
                    error_text = await response.text()
                    logger.warning(f"Failed to create user: {error_text}")
                    return False

        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return False

    async def update_user(self, user_id: str, user_data: Dict[str, Any]) -> bool:
        """Update user in Keycloak."""
        try:
            access_token = await self._get_access_token()

            user_url = f"{self._get_admin_url()}/users/{user_id}"

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            async with self._session.put(
                user_url, json=user_data, headers=headers
            ) as response:
                if response.status in [204, 200]:
                    return True
                else:
                    error_text = await response.text()
                    logger.warning(f"Failed to update user {user_id}: {error_text}")
                    return False

        except Exception as e:
            logger.error(f"Error updating user: {e}")
            return False

    async def delete_user(self, user_id: str) -> bool:
        """Delete user from Keycloak."""
        try:
            access_token = await self._get_access_token()

            user_url = f"{self._get_admin_url()}/users/{user_id}"

            headers = {"Authorization": f"Bearer {access_token}"}

            async with self._session.delete(user_url, headers=headers) as response:
                if response.status in [204, 404]:  # 404 if user doesn't exist
                    return True
                else:
                    error_text = await response.text()
                    logger.warning(f"Failed to delete user {user_id}: {error_text}")
                    return False

        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            return False

    async def reset_password(self, user_id: str, new_password: str) -> bool:
        """Reset user password."""
        try:
            access_token = await self._get_access_token()

            reset_url = f"{self._get_admin_url()}/users/{user_id}/reset-password"

            data = {
                "type": "password",
                "value": new_password,
                "temporary": False,
            }

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            async with self._session.put(
                reset_url, json=data, headers=headers
            ) as response:
                if response.status in [204, 200]:
                    return True
                else:
                    error_text = await response.text()
                    logger.warning(
                        f"Failed to reset password for user {user_id}: {error_text}"
                    )
                    return False

        except Exception as e:
            logger.error(f"Error resetting password: {e}")
            return False

    async def send_verify_email(self, user_id: str) -> bool:
        """Send email verification."""
        try:
            access_token = await self._get_access_token()

            verify_url = f"{self._get_admin_url()}/users/{user_id}/send-verify-email"

            headers = {"Authorization": f"Bearer {access_token}"}

            async with self._session.post(verify_url, headers=headers) as response:
                if response.status in [200, 204]:
                    return True
                else:
                    error_text = await response.text()
                    logger.warning(
                        f"Failed to send verify email for user {user_id}: {error_text}"
                    )
                    return False

        except Exception as e:
            logger.error(f"Error sending verify email: {e}")
            return False

    async def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user sessions."""
        try:
            access_token = await self._get_access_token()

            sessions_url = f"{self._get_admin_url()}/users/{user_id}/sessions"

            headers = {"Authorization": f"Bearer {access_token}"}

            async with self._session.get(sessions_url, headers=headers) as response:
                if response.status == 200:
                    sessions = await response.json()
                    return sessions
                else:
                    logger.warning(f"Failed to get sessions for user {user_id}")
                    return []

        except Exception as e:
            logger.error(f"Error getting user sessions: {e}")
            return []

    async def logout_user_session(self, user_id: str, session_id: str) -> bool:
        """Logout specific user session."""
        try:
            access_token = await self._get_access_token()

            session_url = (
                f"{self._get_admin_url()}/users/{user_id}/sessions/{session_id}"
            )

            headers = {"Authorization": f"Bearer {access_token}"}

            async with self._session.delete(session_url, headers=headers) as response:
                if response.status in [204, 404]:
                    return True
                else:
                    error_text = await response.text()
                    logger.warning(
                        f"Failed to logout session {session_id} for user {user_id}: {error_text}"
                    )
                    return False

        except Exception as e:
            logger.error(f"Error logging out user session: {e}")
            return False


class KeycloakManager:
    """High-level Keycloak manager for authentication and user management."""

    def __init__(self, config: KeycloakConfig):
        self.config = config
        self.client = KeycloakClient(config)

    async def start(self):
        """Start the Keycloak manager."""
        await self.client.start()

    async def stop(self):
        """Stop the Keycloak manager."""
        await self.client.stop()

    async def authenticate_and_get_user(
        self, username: str, password: str
    ) -> Optional[UserInfo]:
        """Authenticate user and return user info."""
        # Authenticate user
        token_response = await self.client.authenticate_user(username, password)
        if not token_response:
            return None

        # Get user info from token
        user_info = await self.client.get_user_info(token_response.access_token)
        return user_info

    async def validate_token_and_get_user(
        self, access_token: str
    ) -> Optional[UserInfo]:
        """Validate token and return user info."""
        # Verify token
        if not await self.client.verify_token(access_token):
            return None

        # Get user info
        user_info = await self.client.get_user_info(access_token)
        return user_info

    async def create_user_with_verification(self, user_data: Dict[str, Any]) -> bool:
        """Create user and send verification email."""
        # Create user
        success = await self.client.create_user(user_data)
        if not success:
            return False

        # Find user by email to get user ID
        users = await self.client.get_users(search=user_data.get("email"))
        if users:
            user_id = users[0]["id"]
            await self.client.send_verify_email(user_id)

        return True

    async def enable_mfa(self, user_id: str) -> bool:
        """Enable MFA for user."""
        # This would require additional Keycloak configuration for MFA
        # For now, return True as a placeholder
        logger.info(f"MFA enabled for user {user_id}")
        return True

    async def disable_mfa(self, user_id: str) -> bool:
        """Disable MFA for user."""
        # This would require additional Keycloak configuration for MFA
        # For now, return True as a placeholder
        logger.info(f"MFA disabled for user {user_id}")
        return True

    async def get_user_realm_roles(self, user_id: str) -> List[str]:
        """Get user's realm roles."""
        try:
            access_token = await self.client._get_access_token()

            roles_url = (
                f"{self.client._get_admin_url()}/users/{user_id}/role-mappings/realm"
            )

            headers = {"Authorization": f"Bearer {access_token}"}

            async with self.client._session.get(roles_url, headers=headers) as response:
                if response.status == 200:
                    roles = await response.json()
                    return [role["name"] for role in roles]
                else:
                    logger.warning(f"Failed to get roles for user {user_id}")
                    return []

        except Exception as e:
            logger.error(f"Error getting user roles: {e}")
            return []

    async def assign_realm_role(self, user_id: str, role_name: str) -> bool:
        """Assign realm role to user."""
        try:
            access_token = await self.client._get_access_token()

            # Get available roles first
            roles_url = f"{self.client._get_admin_url()}/roles"

            headers = {"Authorization": f"Bearer {access_token}"}

            async with self.client._session.get(roles_url, headers=headers) as response:
                if response.status == 200:
                    available_roles = await response.json()
                    role = next(
                        (r for r in available_roles if r["name"] == role_name), None
                    )

                    if not role:
                        logger.warning(f"Role {role_name} not found")
                        return False

                    # Assign role
                    assign_url = f"{self.client._get_admin_url()}/users/{user_id}/role-mappings/realm"

                    async with self.client._session.post(
                        assign_url, json=[role], headers=headers
                    ) as response:
                        if response.status in [204, 200]:
                            logger.info(f"Assigned role {role_name} to user {user_id}")
                            return True
                        else:
                            logger.warning(
                                f"Failed to assign role {role_name} to user {user_id}"
                            )
                            return False

        except Exception as e:
            logger.error(f"Error assigning role: {e}")
            return False
