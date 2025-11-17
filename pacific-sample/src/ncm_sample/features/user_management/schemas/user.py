"""User schemas for API serialization."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, EmailStr

class UserBase(BaseModel):
    """Base user schema."""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    is_active: bool = True
    is_verified: bool = False

class UserCreate(UserBase):
    """Schema for creating a user."""
    password: str = Field(..., min_length=8, max_length=100)

class UserUpdate(BaseModel):
    """Schema for updating a user."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    profile_data: Optional[str] = None

class UserResponse(UserBase):
    """Schema for user response."""
    id: int
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    profile_data: Optional[str] = None
    
    class Config:
        from_attributes = True

class UserListResponse(BaseModel):
    """Schema for user list response."""
    users: list[UserResponse]
    total: int
    page: int
    size: int
    pages: int

class UserLogin(BaseModel):
    """Schema for user login."""
    username: str
    password: str

class UserPasswordChange(BaseModel):
    """Schema for password change."""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)
