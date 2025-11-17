"""
NCM Foundation Library for Microservices

A comprehensive foundation library providing core infrastructure components
for NCM microservices including database management, caching, logging,
messaging, security, and monitoring.
"""

from .core import (
    cache,
    config,
    container,
    database,
    logging,
    messaging,
    monitoring,
    security,
    utils,
)

# Note: CacheManager temporarily disabled due to circular import issues
from .core.config import FoundationConfig, get_settings
from .core.container import DIContainer, get_container, reset_container
from .core.database.manager import DatabaseManager
from .core.logging import LogManager, get_logger, set_correlation_id

__version__ = "0.1.0"
__author__ = "NCM Team"
__email__ = "dev@ncm.com"

__all__ = [
    "cache",
    "container",
    "database",
    "logging",
    "messaging",
    "security",
    "config",
    "monitoring",
    "utils",
    "FoundationConfig",
    "get_settings",
    "DIContainer",
    "get_container",
    "reset_container",
    "DatabaseManager",
    "LogManager",
    "get_logger",
    "set_correlation_id",
]
