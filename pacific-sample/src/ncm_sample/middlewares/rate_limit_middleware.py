"""Rate limiting middleware for NCM Sample."""

from typing import List, Optional
from ncm_foundation.core.security.middleware import RateLimitMiddleware as FoundationRateLimitMiddleware
from ncm_sample.config.settings import get_settings


class RateLimitMiddleware:
    """Rate limiting middleware wrapper for NCM Sample."""

    def __init__(
        self,
        requests_per_minute: int = None,
        burst_limit: int = 10,
        window_size: int = 60,
        exclude_paths: Optional[List[str]] = None,
    ):
        settings = get_settings()

        # Use settings if no explicit rate provided
        if requests_per_minute is None:
            requests_per_minute = getattr(
                settings, 'rate_limit_requests_per_minute', 60)

        self.exclude_paths = exclude_paths or [
            "/health", "/docs", "/openapi.json"]

        self.foundation_middleware = FoundationRateLimitMiddleware(
            requests_per_minute=requests_per_minute,
            burst_limit=burst_limit,
            window_size=window_size,
        )

    def get_middleware(self):
        """Get the foundation rate limit middleware class."""
        return self.foundation_middleware
