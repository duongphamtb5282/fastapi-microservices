"""
Basic usage example for NCM Foundation Library.
"""

import asyncio
import os
from datetime import datetime
from typing import Any, Dict

from ncm_foundation import (
    CacheManager,
    DatabaseManager,
    FoundationConfig,
    LogManager,
    get_logger,
    set_correlation_id,
)
from ncm_foundation.cache import CacheStrategy
from ncm_foundation.database import BaseEntity, SQLRepository


class User(BaseEntity):
    """User entity example."""

    def __init__(self, email: str, name: str, **kwargs):
        super().__init__(**kwargs)
        self.email = email
        self.name = name

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = super().to_dict()
        data.update({"email": self.email, "name": self.name})
        return data


async def main():
    """Main example function."""
    # Set correlation ID for request tracing
    set_correlation_id("example-123")

    logger = get_logger(__name__)
    logger.info("Starting NCM Foundation example")

    try:
        # Initialize configuration
        config = FoundationConfig.from_env()

        # Initialize managers
        db_manager = DatabaseManager(config.database)
        cache_manager = CacheManager(config.cache)
        log_manager = LogManager(config.logging)

        # Start services
        await db_manager.start()
        await cache_manager.start()
        await log_manager.start()

        logger.info("All services started successfully")

        # Database operations
        logger.info("Testing database operations...")

        # Create repository
        user_repo = SQLRepository(User, "users", await db_manager.get_connection())

        # Create user
        user = User(email="john.doe@example.com", name="John Doe", created_by="system")

        created_user = await user_repo.create(user)
        logger.info(f"Created user: {created_user.id}")

        # Retrieve user
        retrieved_user = await user_repo.get_by_id(created_user.id)
        if retrieved_user:
            logger.info(f"Retrieved user: {retrieved_user.name}")

        # Cache operations
        logger.info("Testing cache operations...")

        # Set cache strategy
        cache_manager.set_strategy(CacheStrategy.WRITE_THROUGH)

        # Cache user data
        user_data = {
            "id": str(created_user.id),
            "email": created_user.email,
            "name": created_user.name,
            "created_at": created_user.created_at.isoformat(),
        }

        await cache_manager.set(f"user:{created_user.id}", user_data, ttl=3600)
        logger.info("User data cached")

        # Retrieve from cache
        cached_data = await cache_manager.get(f"user:{created_user.id}")
        if cached_data:
            logger.info(f"Retrieved from cache: {cached_data['name']}")

        # Cache with factory function
        cached_user = await cache_manager.get_or_set(
            f"user:factory:{created_user.id}", lambda: user_data, ttl=1800
        )
        logger.info(f"Factory cached user: {cached_user['name']}")

        # List users
        users = await user_repo.list(limit=10)
        logger.info(f"Found {len(users)} users")

        # Get statistics
        db_stats = db_manager.get_stats()
        cache_stats = cache_manager.get_stats()
        log_stats = log_manager.get_stats()

        logger.info("Service statistics:")
        logger.info(f"Database: {db_stats}")
        logger.info(f"Cache: {cache_stats}")
        logger.info(f"Logging: {log_stats}")

        # Health checks
        db_health = await db_manager.health_check()
        cache_health = await cache_manager.health_check()

        logger.info(f"Health status - Database: {db_health}, Cache: {cache_health}")

    except Exception as e:
        logger.error(f"Example failed: {e}", exc_info=True)
        raise

    finally:
        # Cleanup
        logger.info("Stopping services...")

        if "cache_manager" in locals():
            await cache_manager.stop()

        if "db_manager" in locals():
            await db_manager.stop()

        if "log_manager" in locals():
            await log_manager.stop()

        logger.info("Example completed")


if __name__ == "__main__":
    # Set up environment variables for the example
    os.environ.setdefault(
        "DATABASE_URL", "postgresql://postgres:password@localhost:5432/ncm"
    )
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
    os.environ.setdefault("SECRET_KEY", "your-secret-key-here")
    os.environ.setdefault("JWT_SECRET", "your-jwt-secret-here")

    # Run the example
    asyncio.run(main())
