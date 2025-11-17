"""Health checks and monitoring utilities."""

from typing import Any, Dict, List

# Note: CacheManager import temporarily disabled to avoid circular imports
# from . import cache
# CacheManager = cache.CacheManager
from .database import DatabaseManager
from .logging import get_logger

logger = get_logger(__name__)


class HealthCheckManager:
    """Health check manager for monitoring service health."""

    def __init__(self, db_manager: DatabaseManager, cache_manager=None):
        self.db_manager = db_manager
        self.cache_manager = cache_manager

    async def check_database(self) -> Dict[str, Any]:
        """Check database health."""
        try:
            is_healthy = await self.db_manager.health_check()
            return {
                "status": "healthy" if is_healthy else "unhealthy",
                "service": "database",
                "details": (
                    "Connection pool is operational"
                    if is_healthy
                    else "Connection failed"
                ),
            }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {"status": "unhealthy", "service": "database", "error": str(e)}

    async def check_cache(self) -> Dict[str, Any]:
        """Check Redis cache health."""
        try:
            if self.cache_manager is None:
                return {
                    "status": "not_configured",
                    "service": "cache",
                    "details": "Cache manager not configured",
                }

            is_healthy = await self.cache_manager.health_check()
            return {
                "status": "healthy" if is_healthy else "unhealthy",
                "service": "cache",
                "details": (
                    "Redis connection is operational"
                    if is_healthy
                    else "Connection failed"
                ),
            }
        except Exception as e:
            logger.error(f"Cache health check failed: {e}")
            return {"status": "unhealthy", "service": "cache", "error": str(e)}

    async def get_overall_health(self) -> Dict[str, Any]:
        """Get overall system health."""
        db_health = await self.check_database()
        cache_health = await self.check_cache()

        overall_status = "healthy"
        if db_health["status"] != "healthy" or cache_health["status"] != "healthy":
            overall_status = "unhealthy"

        return {
            "status": overall_status,
            "services": {"database": db_health, "cache": cache_health},
        }
