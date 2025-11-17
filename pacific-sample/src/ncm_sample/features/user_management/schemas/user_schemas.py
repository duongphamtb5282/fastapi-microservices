"""
Pydantic schemas for NCM Sample Project.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Base user schema."""

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    avatar_url: Optional[str] = Field(None, max_length=500)


class UserCreate(UserBase):
    """User creation schema."""

    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    """User update schema."""

    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    avatar_url: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """User response schema."""

    id: int
    is_active: bool
    is_verified: bool
    last_login: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]
    updated_by: Optional[str]
    version: int

    class Config:
        from_attributes = True


class RoleBase(BaseModel):
    """Base role schema."""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    permissions: Optional[str] = None


class RoleCreate(RoleBase):
    """Role creation schema."""

    pass


class RoleUpdate(BaseModel):
    """Role update schema."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    permissions: Optional[str] = None
    is_active: Optional[bool] = None


class RoleResponse(RoleBase):
    """Role response schema."""

    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]
    updated_by: Optional[str]
    version: int

    class Config:
        from_attributes = True


class UserRoleBase(BaseModel):
    """Base user role schema."""

    user_id: int
    role_id: int
    assigned_by: Optional[str] = None
    expires_at: Optional[datetime] = None


class UserRoleCreate(UserRoleBase):
    """User role creation schema."""

    pass


class UserRoleUpdate(BaseModel):
    """User role update schema."""

    is_active: Optional[bool] = None
    expires_at: Optional[datetime] = None


class UserRoleResponse(UserRoleBase):
    """User role response schema."""

    id: int
    assigned_at: datetime
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]
    updated_by: Optional[str]
    version: int

    class Config:
        from_attributes = True


class UserWithRoles(UserResponse):
    """User with roles schema."""

    roles: List[RoleResponse] = []


class RoleWithUsers(RoleResponse):
    """Role with users schema."""

    users: List[UserResponse] = []


class LoginRequest(BaseModel):
    """Login request schema."""

    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response schema."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class TokenData(BaseModel):
    """Token data schema."""

    username: Optional[str] = None
    user_id: Optional[int] = None


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str
    timestamp: datetime
    services: dict
    version: str
