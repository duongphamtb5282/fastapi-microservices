"""
Common API Router
"""

from .demo_router import router as demo_router
from .health_router import router as health_router

__all__ = ["demo_router", "health_router"]
