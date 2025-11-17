"""
Database foundation usage examples.
"""

import asyncio
from datetime import datetime
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.ext.asyncio import AsyncSession

from .config import DatabaseConfig, DatabaseType
from .models.base import AuditMixin, BaseModel, SoftDeleteMixin
from .providers.mongodb_provider import MongoDBProvider
from .providers.sqlalchemy_provider import SQLAlchemyProvider
from .repositories.mongodb_repo import MongoDBRepository
from .repositories.sqlalchemy_repo import SQLAlchemyRepository
from .schemas.base import AuditSchema, BaseSchema, SoftDeleteSchema
from .security.access_control import RowLevelSecurity, SecurityLevel
from .security.encryption import EncryptedString
from .session import DatabaseManager


# Example SQLAlchemy Model
class User(BaseModel, SoftDeleteMixin):
    """Example user model."""

    __tablename__ = "users"

    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(EncryptedString(255), nullable=False)  # Encrypted field
    is_active = Column(Boolean, default=True, nullable=False)
    last_login = Column(DateTime, nullable=True)


# Example Pydantic Schema
class UserSchema(BaseSchema):
    """User Pydantic schema."""

    id: int
    username: str
    email: str
    is_active: bool = True
    last_login: Optional[datetime] = None


class UserCreateSchema(BaseSchema):
    """User creation schema."""

    username: str
    email: str
    password: str


class UserUpdateSchema(BaseSchema):
    """User update schema."""

    username: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None


# Example MongoDB Document
class MongoUser:
    """Example MongoDB user document."""

    def __init__(self, **kwargs):
        self.id = kwargs.get("id")
        self.username = kwargs.get("username")
        self.email = kwargs.get("email")
        self.password_hash = kwargs.get("password_hash")
        self.is_active = kwargs.get("is_active", True)
        self.last_login = kwargs.get("last_login")
        self.created_at = kwargs.get("created_at", datetime.utcnow())
        self.updated_at = kwargs.get("updated_at", datetime.utcnow())
        self.created_by = kwargs.get("created_by")
        self.updated_by = kwargs.get("updated_by")
        self.version = kwargs.get("version", 1)
        self.is_deleted = kwargs.get("is_deleted", False)
        self.deleted_at = kwargs.get("deleted_at")
        self.deleted_by = kwargs.get("deleted_by")

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "password_hash": self.password_hash,
            "is_active": self.is_active,
            "last_login": self.last_login,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "created_by": self.created_by,
            "updated_by": self.updated_by,
            "version": self.version,
            "is_deleted": self.is_deleted,
            "deleted_at": self.deleted_at,
            "deleted_by": self.deleted_by,
        }


async def sqlalchemy_example():
    """Example using SQLAlchemy provider."""
    print("=== SQLAlchemy Example ===")

    # Configure database
    config = DatabaseConfig(
        db_type=DatabaseType.POSTGRESQL,
        host="localhost",
        port=5432,
        database="ncm_example",
        username="postgres",
        password="password",
    )

    # Create provider
    provider = SQLAlchemyProvider(config)

    # Create database manager
    db_manager = DatabaseManager(provider)

    try:
        # Connect to database
        await db_manager.connect()
        print("Connected to PostgreSQL database")

        # Get session
        async with db_manager.get_session() as session:
            # Create repository
            user_repo = SQLAlchemyRepository(User, session)

            # Create user
            user_data = {
                "username": "john_doe",
                "email": "john@example.com",
                "password_hash": "hashed_password",
                "created_by": "system",
            }

            user = await user_repo.create(user_data)
            print(f"Created user: {user.username} (ID: {user.id})")

            # Get user by ID
            retrieved_user = await user_repo.get_by_id(user.id)
            print(f"Retrieved user: {retrieved_user.username}")

            # Update user
            update_data = {"is_active": False, "updated_by": "admin"}
            updated_user = await user_repo.update(user.id, update_data)
            print(f"Updated user: {updated_user.is_active}")

            # List users
            users = await user_repo.list(limit=10)
            print(f"Found {len(users)} users")

            # Search users
            search_results = await user_repo.search(
                "john", fields=["username", "email"]
            )
            print(f"Search results: {len(search_results)} users")

            # Soft delete user
            deleted = await user_repo.delete(user.id)
            print(f"User deleted: {deleted}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Disconnect
        await db_manager.disconnect()
        print("Disconnected from database")


async def mongodb_example():
    """Example using MongoDB provider."""
    print("\n=== MongoDB Example ===")

    # Configure database
    config = DatabaseConfig(
        db_type=DatabaseType.MONGODB,
        host="localhost",
        port=27017,
        database="ncm_example",
        username="",
        password="",
    )

    # Create provider
    provider = MongoDBProvider(config)

    # Create database manager
    db_manager = DatabaseManager(provider)

    try:
        # Connect to database
        await db_manager.connect()
        print("Connected to MongoDB database")

        # Get database
        database = await provider.get_session()

        # Create repository
        user_repo = MongoDBRepository(MongoUser, database, "users")

        # Create user
        user_data = {
            "username": "jane_doe",
            "email": "jane@example.com",
            "password_hash": "hashed_password",
            "created_by": "system",
        }

        user = await user_repo.create(user_data)
        print(f"Created user: {user.username} (ID: {user.id})")

        # Get user by ID
        retrieved_user = await user_repo.get_by_id(user.id)
        print(f"Retrieved user: {retrieved_user.username}")

        # Update user
        update_data = {"is_active": False, "updated_by": "admin"}
        updated_user = await user_repo.update(user.id, update_data)
        print(f"Updated user: {updated_user.is_active}")

        # List users
        users = await user_repo.list(limit=10)
        print(f"Found {len(users)} users")

        # Search users
        search_results = await user_repo.search("jane", fields=["username", "email"])
        print(f"Search results: {len(search_results)} users")

        # Delete user
        deleted = await user_repo.delete(user.id)
        print(f"User deleted: {deleted}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Disconnect
        await db_manager.disconnect()
        print("Disconnected from database")


async def security_example():
    """Example using security features."""
    print("\n=== Security Example ===")

    # Configure database with security
    config = DatabaseConfig(
        db_type=DatabaseType.POSTGRESQL,
        host="localhost",
        port=5432,
        database="ncm_example",
        username="postgres",
        password="password",
        security_enabled=True,
        rls_enabled=True,
    )

    # Create provider
    provider = SQLAlchemyProvider(config)
    db_manager = DatabaseManager(provider)

    try:
        # Connect to database
        await db_manager.connect()
        print("Connected to database with security enabled")

        # Set audit user
        db_manager.session_manager.set_audit_user("admin_user")

        # Setup row-level security
        user_context = {
            "user_id": "admin_user",
            "roles": ["admin"],
            "organization_id": 1,
            "security_level": SecurityLevel.INTERNAL,
        }

        rls = RowLevelSecurity(user_context)
        print("Row-level security configured")

        # Get session and apply security
        async with db_manager.get_session() as session:
            # Apply RLS policies
            rls.setup_rls_policies(session, "users")
            print("RLS policies applied")

            # Create repository with security context
            user_repo = SQLAlchemyRepository(User, session)

            # Create user with audit logging
            user_data = {
                "username": "secure_user",
                "email": "secure@example.com",
                "password_hash": "encrypted_password",
                "created_by": "admin_user",
            }

            user = await user_repo.create(user_data)
            print(f"Created secure user: {user.username}")
            print(f"Audit fields: created_by={user.created_by}, version={user.version}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        await db_manager.disconnect()
        print("Disconnected from database")


async def connection_pooling_example():
    """Example using connection pooling."""
    print("\n=== Connection Pooling Example ===")

    # Configure database with pooling
    config = DatabaseConfig(
        db_type=DatabaseType.POSTGRESQL,
        host="localhost",
        port=5432,
        database="ncm_example",
        username="postgres",
        password="password",
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
    )

    # Create provider
    provider = SQLAlchemyProvider(config)
    db_manager = DatabaseManager(provider)

    try:
        # Connect to database
        await db_manager.connect()
        print("Connected to database with connection pooling")

        # Get pool statistics
        if hasattr(provider, "get_pool_stats"):
            pool_stats = await provider.get_pool_stats()
            print(f"Pool statistics: {pool_stats}")

        # Simulate concurrent operations
        async def create_user(user_id: int):
            async with db_manager.get_session() as session:
                user_repo = SQLAlchemyRepository(User, session)
                user_data = {
                    "username": f"user_{user_id}",
                    "email": f"user{user_id}@example.com",
                    "password_hash": "hashed_password",
                    "created_by": "system",
                }
                user = await user_repo.create(user_data)
                return user

        # Create multiple users concurrently
        tasks = [create_user(i) for i in range(5)]
        users = await asyncio.gather(*tasks)
        print(f"Created {len(users)} users concurrently")

        # Get updated pool statistics
        if hasattr(provider, "get_pool_stats"):
            pool_stats = await provider.get_pool_stats()
            print(f"Updated pool statistics: {pool_stats}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        await db_manager.disconnect()
        print("Disconnected from database")


async def main():
    """Run all examples."""
    print("Database Foundation Examples")
    print("=" * 50)

    # Run examples
    await sqlalchemy_example()
    await mongodb_example()
    await security_example()
    await connection_pooling_example()

    print("\nAll examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
