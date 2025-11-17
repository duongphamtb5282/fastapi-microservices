"""
User Management API Router
"""

from .user_router import init_feature
from .user_router import router as user_router

__all__ = ["user_router", "init_feature"]
