"""User repository implementation."""

from typing import List, Optional

from auth_service.domains.user.models.user import User
from ncm_foundation import get_logger
from sqlalchemy.orm import # In the provided code snippet, `Session` is being imported from
# `sqlalchemy.orm` module. It is used as a parameter type hint in the
# `__init__` method of the `UserRepository` class to indicate that the
# `db_session` parameter should be an instance of a SQLAlchemy session.
Session

logger = get_logger(__name__)


class UserRepository:
    """User repository for database operations."""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
    
    async def create(self, user_data: dict) -> User:
        """Create a new user."""
        user = User(**user_data)
        self.db_session.add(user)
        self.db_session.commit()
        self.db_session.refresh(user)
        return user
    
    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return self.db_session.query(User).filter(User.id == user_id).first()
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return self.db_session.query(User).filter(User.email == email).first()
    
    async def list_all(self) -> List[User]:
        """List all users."""
        return self.db_session.query(User).all()
    
    async def update(self, user_id: int, update_data: dict) -> Optional[User]:
        """Update user."""
        user = self.db_session.query(User).filter(User.id == user_id).first()
        if user:
            for key, value in update_data.items():
                setattr(user, key, value)
            self.db_session.commit()
            self.db_session.refresh(user)
        return user
    
    async def delete(self, user_id: int) -> bool:
        """Delete user."""
        user = self.db_session.query(User).filter(User.id == user_id).first()
        if user:
            self.db_session.delete(user)
            self.db_session.commit()
            return True
        return False
