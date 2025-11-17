"""
Authentication API Router
"""

from .auth_router import init_feature
from .auth_router import router as auth_router

__all__ = ["auth_router", "init_feature"]
