"""Security middleware for NCM Sample."""

from ncm_foundation.core.security.middleware import SecurityMiddleware as FoundationSecurityMiddleware

class SecurityMiddleware:
    """Security middleware wrapper for NCM Sample."""

    def __init__(self):
        pass

    def get_middleware(self):
        """Get the foundation security middleware class."""
        return FoundationSecurityMiddleware
