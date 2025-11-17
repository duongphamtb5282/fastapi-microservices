"""User controller implementation."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from ncm_sample.features.user_management.services.user_service import UserService
from ncm_sample.features.user_management.schemas.user import (
    UserCreate, UserResponse, UserUpdate, UserListResponse, UserPasswordChange
)
from ncm_sample.core.dependencies import get_current_user, require_permissions, get_session_db
from ncm_foundation.core.database.manager import DatabaseManager
from ncm_sample.features.shared.controllers.base_controller import BaseController
from sqlalchemy.ext.asyncio import AsyncSession


class UserController(BaseController[UserService]):
    """User controller with REST endpoints."""

    def __init__(self, user_service_class: type = UserService):
        router = APIRouter(prefix="/users", tags=["Users"])
        super().__init__(user_service_class, router)

    def _setup_routes(self):
        @self.router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
        async def create_user(
            user_data: UserCreate,
            session_db: AsyncSession = Depends(get_session_db)
            # _ = Depends(require_permissions(["user:create"]))
        ):
            """Create a new user."""
            try:
                user_service = self.service_class(session=session_db)
                user = await user_service.create_user(user_data)
                return UserResponse.from_orm(user)
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

        @self.router.get("/{user_id}", response_model=UserResponse)
        async def get_user(
            user_id: int,
            session_db: AsyncSession = Depends(get_session_db),
            # current_user: dict = Depends(require_permissions(["user:read"]))
        ):
            """Get user by ID."""
            user_service = self.service_class(session=session_db)
            user = await user_service.get_user_by_id(user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
            return UserResponse.from_orm(user)

        @self.router.get("/", response_model=UserListResponse)
        async def list_users(
            skip: int = Query(0, ge=0, description="Number of users to skip"),
            limit: int = Query(100, ge=1, le=1000,
                               description="Number of users to return"),
            search: str = Query(None, description="Search term for users"),
            is_active: bool = Query(
                None, description="Filter by active status"),
            session_db: AsyncSession = Depends(get_session_db),
            current_user: dict = Depends(require_permissions(["user:list"]))
        ):
            """List users with pagination and filtering."""
            user_service = self.service_class(session=session_db)
            filters = {}
            if is_active is not None:
                filters["is_active"] = is_active

            if search:
                users = await user_service.search_users(search, skip=skip, limit=limit)
                total = await user_service.count_users(filters)
            else:
                users = await user_service.list_users(skip=skip, limit=limit, filters=filters)
                total = await user_service.count_users(filters)

            pages = (total + limit - 1) // limit
            current_page = (skip // limit) + 1

            return UserListResponse(
                users=[UserResponse.from_orm(user) for user in users],
                total=total,
                page=current_page,
                size=limit,
                pages=pages
            )

        @self.router.put("/{user_id}", response_model=UserResponse)
        async def update_user(
            user_id: int,
            user_data: UserUpdate,
            session_db: AsyncSession = Depends(get_session_db),
            current_user: dict = Depends(require_permissions(["user:update"]))
        ):
            """Update user."""
            user_service = self.service_class(session=session_db)
            user = await user_service.update_user(user_id, user_data)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
            return UserResponse.from_orm(user)

        @self.router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
        async def delete_user(
            user_id: int,
            session_db: AsyncSession = Depends(get_session_db),
            current_user: dict = Depends(require_permissions(["user:delete"]))
        ):
            """Delete user."""
            user_service = self.service_class(session=session_db)
            async with session_db.begin():
                success = await user_service.delete_user(user_id)
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        @self.router.post("/{user_id}/change-password", status_code=status.HTTP_200_OK)
        async def change_password(
            user_id: int,
            password_data: UserPasswordChange,
            session_db: AsyncSession = Depends(get_session_db),
            current_user: dict = Depends(require_permissions(["user:update"]))
        ):
            """Change user password."""
            user_service = self.service_class(session=session_db)
            async with session_db.begin():
                success = await user_service.change_password(
                    user_id,
                    password_data.current_password,
                    password_data.new_password
                )
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid current password or user not found"
                )
            return {"message": "Password changed successfully"}

        @self.router.post("/{user_id}/activate", status_code=status.HTTP_200_OK)
        async def activate_user(
            user_id: int,
            session_db: AsyncSession = Depends(get_session_db),
            current_user: dict = Depends(require_permissions(["user:update"]))
        ):
            """Activate user account."""
            user_service = self.service_class(session=session_db)
            async with session_db.begin():
                success = await user_service.activate_user(user_id)
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
            return {"message": "User activated successfully"}

        @self.router.post("/{user_id}/deactivate", status_code=status.HTTP_200_OK)
        async def deactivate_user(
            user_id: int,
            session_db: AsyncSession = Depends(get_session_db),
            current_user: dict = Depends(require_permissions(["user:update"]))
        ):
            """Deactivate user account."""
            user_service = self.service_class(session=session_db)
            async with session_db.begin():
                success = await user_service.deactivate_user(user_id)
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
            return {"message": "User deactivated successfully"}

        @self.router.get("/email/{email}", response_model=UserResponse)
        async def get_user_by_email(
            email: str,
            session_db: AsyncSession = Depends(get_session_db),
            current_user: dict = Depends(require_permissions(["user:read"]))
        ):
            """Get user by email."""
            user_service = self.service_class(session=session_db)
            user = await user_service.get_user_by_email(email)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
            return UserResponse.from_orm(user)
