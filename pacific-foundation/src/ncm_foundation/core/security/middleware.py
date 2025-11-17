"""
Security middleware components.
"""

import time
from collections import defaultdict, deque
from typing import List, Optional

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware as StarletteCORSMiddleware

from ncm_foundation.core.logging import logger


class SecurityMiddleware(BaseHTTPMiddleware):
    """Base security middleware."""

    async def dispatch(self, request: Request, call_next):
        """Process the request through security checks."""
        # Add security headers
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        return response


class CORSMiddleware:
    """CORS middleware configuration."""

    def __init__(
        self,
        allow_origins: List[str] = ["*"],
        allow_credentials: bool = True,
        allow_methods: List[str] = ["*"],
        allow_headers: List[str] = ["*"],
    ):
        self.allow_origins = allow_origins
        self.allow_credentials = allow_credentials
        self.allow_methods = allow_methods
        self.allow_headers = allow_headers
        logger.info("CORSMiddleware configured", origins=allow_origins)

    def get_middleware(self):
        """Get the Starlette CORS middleware instance."""
        return StarletteCORSMiddleware(
            app=None,  # Will be set by FastAPI
            allow_origins=self.allow_origins,
            allow_credentials=self.allow_credentials,
            allow_methods=self.allow_methods,
            allow_headers=self.allow_headers,
        )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware."""

    def __init__(
        self,
        requests_per_minute: int = 60,
        burst_limit: int = 10,
        window_size: int = 60,
    ):
        super().__init__(None)
        self.requests_per_minute = requests_per_minute
        self.burst_limit = burst_limit
        self.window_size = window_size
        self.requests = defaultdict(lambda: deque())
        logger.info(
            "RateLimitMiddleware initialized",
            requests_per_minute=requests_per_minute,
            burst_limit=burst_limit,
        )

    async def dispatch(self, request: Request, call_next):
        """Apply rate limiting to the request."""
        client_ip = request.client.host
        current_time = time.time()

        # Clean old requests
        while (
            self.requests[client_ip]
            and self.requests[client_ip][0] < current_time - self.window_size
        ):
            self.requests[client_ip].popleft()

        # Check rate limits
        if len(self.requests[client_ip]) >= self.requests_per_minute:
            logger.warning("Rate limit exceeded", client_ip=client_ip)
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded"},
            )

        # Add current request
        self.requests[client_ip].append(current_time)

        # Process request
        response = await call_next(request)
        return response


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Authentication middleware."""

    def __init__(self, auth_manager, exclude_paths: Optional[List[str]] = None):
        super().__init__(None)
        self.auth_manager = auth_manager
        self.exclude_paths = exclude_paths or ["/health", "/docs", "/openapi.json"]
        logger.info("AuthenticationMiddleware initialized", exclude_paths=exclude_paths)

    async def dispatch(self, request: Request, call_next):
        """Check authentication for protected routes."""
        # Skip authentication for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)

        # Extract token from Authorization header
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            logger.warning(
                "Missing or invalid authorization header", path=request.url.path
            )
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing or invalid authorization token"},
            )

        token = authorization.split(" ")[1]
        payload = self.auth_manager.verify_token(token)

        if not payload:
            logger.warning("Invalid token", path=request.url.path)
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid or expired token"},
            )

        # Add user info to request state
        request.state.user = payload

        return await call_next(request)
