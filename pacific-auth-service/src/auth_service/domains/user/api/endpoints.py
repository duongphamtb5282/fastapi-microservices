"""User API endpoints."""

from typing import List

from auth_service.core.dependencies import get_user_service
from auth_service.core.exceptions import (AuthenticationError,
                                         UserAlreadyExistsError,
                                         UserNotFoundError)
from auth_service.domains.user.services.user_service import UserService
from fastapi import APIRouter, Depends, status
from ncm_contracts.auth.schemas import (AuthResponse, LoginRequest,
                                        UserCreateRequest, UserResponse,
                                        UserUpdateRequest)

router = APIRouter()


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: UserCreateRequest,
    user_service: UserService = Depends(get_user_service)
):
    """Create a new user."""
    user = await user_service.create_user(request)
    return user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    user_service: UserService = Depends(get_user_service)
):
    """Get user by ID."""
    return await user_service.get_user(user_id)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    request: UserUpdateRequest,
    user_service: UserService = Depends(get_user_service)
):
    """Update user."""
    return await user_service.update_user(user_id, request)


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    user_service: UserService = Depends(get_user_service)
):
    """User login."""
    return await user_service.authenticate(request)


@router.get("/", response_model=List[UserResponse])
async def list_users(
    user_service: UserService = Depends(get_user_service)
):
    """List all users."""
    users = await user_service.list_users()
    return users
