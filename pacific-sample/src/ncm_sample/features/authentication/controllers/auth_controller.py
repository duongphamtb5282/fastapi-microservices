"""Authentication controller implementation."""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from ncm_sample.features.authentication.services.auth_services import AuthService
from ncm_sample.features.authentication.schemas import (
    LoginRequest,
    LoginResponse,
    TokenRefreshRequest,
    TokenRefreshResponse,
    HealthResponse,
    LogoutResponse,
    UserInfoResponse,
)
from ncm_sample.core.dependencies import get_session_db
from ncm_foundation.core.logging.manager import correlation_id_var
from ncm_sample.config import settings

class AuthController:
    """Authentication controller with REST endpoints."""

    def __init__(self, auth_service: AuthService):
        self.auth_service = auth_service
        self.router = APIRouter(prefix="/auth", tags=["Authentication"])

    def get_router(self) -> APIRouter:
        """Get the configured router."""
        self._setup_routes()
        return self.router

    def _setup_routes(self):
        @self.router.post("/login", response_model=LoginResponse)
        async def login(
            login_data: LoginRequest,
            session_db = Depends(get_session_db)
        ):
            """Login endpoint."""
            correlation_id = correlation_id_var.get()

            try:
                result = await self.auth_service.login(
                    login_data.username,
                    login_data.password,
                    correlation_id=correlation_id,
                    session=session_db
                )
                if not result:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Incorrect username or password",
                    )

                return LoginResponse(**result)

            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Login failed"
                )

        @self.router.post("/refresh", response_model=TokenRefreshResponse)
        async def refresh_token(refresh_data: TokenRefreshRequest):
            """Refresh access token endpoint."""
            correlation_id = correlation_id_var.get()

            try:
                result = await self.auth_service.refresh_access_token(
                    refresh_data.refresh_token,
                    correlation_id=correlation_id
                )
                if not result:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid or expired refresh token",
                    )

                return TokenRefreshResponse(**result)

            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Token refresh failed"
                )

        @self.router.post("/logout", response_model=LogoutResponse)
        async def logout():
            """Logout endpoint."""
            correlation_id = correlation_id_var.get()

            # In a stateless JWT implementation, logout is mainly for audit purposes
            # The actual token invalidation happens on the client side
            return LogoutResponse(message="Logged out successfully")

        @self.router.get("/me", response_model=UserInfoResponse)
        async def get_current_user_info():
            """Get current user information."""
            correlation_id = correlation_id_var.get()

            # In a real implementation, you would decode the JWT token to get user info
            # For now, return a placeholder response
            return UserInfoResponse(
                id=1,
                username="current_user",
                email="user@example.com",
                first_name="Current",
                last_name="User",
                is_active=True,
                is_verified=True,
                last_login=datetime.utcnow()
            )

        @self.router.get("/health", response_model=HealthResponse)
        async def auth_health_check():
            """Health check endpoint for authentication."""
            correlation_id = correlation_id_var.get()

            try:
                # Check if auth service is available
                auth_healthy = self.auth_service is not None

                services = {
                    "auth_service": auth_healthy,
                    "jwt_validation": True,  # JWT validation is always available
                }

                overall_status = "healthy" if all(services.values()) else "unhealthy"

                return HealthResponse(
                    status=overall_status,
                    timestamp=datetime.utcnow(),
                    services=services,
                    version=settings.app_version,
                )

            except Exception as e:
                return HealthResponse(
                    status="unhealthy",
                    timestamp=datetime.utcnow(),
                    services={"error": str(e)},
                    version=settings.app_version,
                )
