"""Common middleware for FastAPI applications."""

import time
import uuid
from typing import Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .logging import get_correlation_id, get_logger, set_correlation_id

logger = get_logger(__name__)


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add correlation ID to all requests for tracing.
    Generates a unique correlation ID for each request and stores it in context.
    """

    def __init__(
        self,
        app: ASGIApp,
        header_name: str = "X-Correlation-ID",
        generate_id: Callable[[], str] = lambda: str(uuid.uuid4()),
        validate_header: bool = True,
    ):
        super().__init__(app)
        self.header_name = header_name
        self.generate_id = generate_id
        self.validate_header = validate_header

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract or generate correlation ID
        correlation_id = self._get_correlation_id(request)

        # Set correlation ID in context
        set_correlation_id(correlation_id)

        # Add correlation ID to request state for access in endpoints
        request.state.correlation_id = correlation_id

        # Add start time for request duration tracking
        start_time = time.time()

        # Process request
        try:
            response = await call_next(request)

            # Add correlation ID to response headers
            response.headers[self.header_name] = correlation_id

            # Calculate request duration
            duration = time.time() - start_time

            # Log request completion
            logger.info(
                "Request completed",
                extra={
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "url": str(request.url),
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                    "client_ip": request.client.host if request.client else None,
                    "user_agent": request.headers.get("user-agent"),
                },
            )

            return response

        except Exception as e:
            # Log request error
            duration = time.time() - start_time
            logger.error(
                f"Request failed: {str(e)}",
                extra={
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "url": str(request.url),
                    "duration_ms": round(duration * 1000, 2),
                    "error": str(e),
                    "client_ip": request.client.host if request.client else None,
                },
                exc_info=True,
            )
            raise

    def _get_correlation_id(self, request: Request) -> str:
        """Extract correlation ID from request headers or generate new one."""
        # Check if correlation ID is already in headers
        existing_id = request.headers.get(self.header_name)

        if existing_id and self.validate_header:
            # Validate existing correlation ID format
            try:
                uuid.UUID(existing_id)
                return existing_id
            except ValueError:
                logger.warning(
                    f"Invalid correlation ID format in header: {existing_id}"
                )

        # Generate new correlation ID
        return self.generate_id()
