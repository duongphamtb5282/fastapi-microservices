"""Global error handling middleware for FastAPI applications."""

import traceback
from typing import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ncm_foundation.core.logging import get_logger

logger = get_logger(__name__)


class GlobalErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Global error handling middleware that catches all exceptions and returns proper error responses."""

    def __init__(self, app: ASGIApp, debug: bool = False):
        super().__init__(app)
        self.debug = debug

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            # Process the request
            response = await call_next(request)
            return response

        except Exception as exc:
            # Log the error with full traceback in debug mode
            if self.debug:
                logger.error(
                    f"Unhandled exception in {request.method} {request.url.path}",
                    extra={
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                        "traceback": traceback.format_exc(),
                        "method": request.method,
                        "url": str(request.url),
                        "headers": dict(request.headers),
                    }
                )
            else:
                logger.error(
                    f"Unhandled exception in {request.method} {request.url.path}",
                    extra={
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                        "method": request.method,
                        "url": str(request.url),
                    }
                )

            # Return appropriate error response based on exception type
            return self._create_error_response(exc, request)

    def _create_error_response(self, exc: Exception, request: Request) -> JSONResponse:
        """Create appropriate error response based on exception type."""

        # Handle HTTP exceptions (they have status_code attribute)
        if hasattr(exc, 'status_code'):
            status_code = exc.status_code
            detail = str(exc.detail) if hasattr(exc, 'detail') else str(exc)
        else:
            # Handle other exceptions
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            detail = "Internal server error"

        # Create error response
        error_response = {
            "detail": detail,
            "type": type(exc).__name__,
            "path": request.url.path,
            "method": request.method,
        }

        # Add request ID if available (from correlation middleware)
        if hasattr(request.state, 'correlation_id'):
            error_response["request_id"] = request.state.correlation_id

        # In debug mode, add traceback
        if self.debug:
            error_response["traceback"] = traceback.format_exc()

        return JSONResponse(
            status_code=status_code,
            content=error_response,
            headers={
                "X-Error-Type": type(exc).__name__,
            }
        )
