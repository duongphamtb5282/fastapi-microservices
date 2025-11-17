"""Authentication schemas for NCM Sample Project."""

from datetime import datetime
from typing import Dict, Optional
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Login request schema."""

    username: str = Field(..., min_length=1, max_length=50, description="Username or email")
    password: str = Field(..., min_length=1, max_length=100, description="Password")


class LoginResponse(BaseModel):
    """Login response schema."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration time in seconds")
    refresh_expires_in: int = Field(..., description="Refresh token expiration time in seconds")
    user: Dict = Field(..., description="User information")


class TokenRefreshRequest(BaseModel):
    """Token refresh request schema."""

    refresh_token: str = Field(..., description="Refresh token")


class TokenRefreshResponse(BaseModel):
    """Token refresh response schema."""

    access_token: str = Field(..., description="New JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration time in seconds")
    user: Dict = Field(..., description="User information")


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str = Field(..., description="Overall health status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    services: Dict[str, bool] = Field(..., description="Individual service health status")
    version: str = Field(..., description="Application version")


class LogoutResponse(BaseModel):
    """Logout response schema."""

    message: str = Field(..., description="Logout confirmation message")


class UserInfoResponse(BaseModel):
    """Current user information response schema."""

    id: int = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    first_name: str = Field(..., description="First name")
    last_name: str = Field(..., description="Last name")
    is_active: bool = Field(..., description="Whether user is active")
    is_verified: bool = Field(..., description="Whether user is verified")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
