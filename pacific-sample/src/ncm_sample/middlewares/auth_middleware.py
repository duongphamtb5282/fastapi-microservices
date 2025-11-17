"""Authentication middleware for NCM Sample."""

from typing import List, Optional
from ncm_foundation.core.security.middleware import AuthenticationMiddleware as FoundationAuthMiddleware

class AuthenticationMiddleware:
    """Authentication middleware wrapper for NCM Sample."""

    def __init__(
        self,
        auth_manager=None,
        exclude_paths: Optional[List[str]] = None,
    ):
        self.exclude_paths = exclude_paths or ["/health", "/docs", "/openapi.json", "/auth/login"]

        self.foundation_middleware = FoundationAuthMiddleware(
            auth_manager=auth_manager,
            exclude_paths=self.exclude_paths,
        )

    def get_middleware(self):
        """Get the foundation authentication middleware class."""
        return self.foundation_middleware
