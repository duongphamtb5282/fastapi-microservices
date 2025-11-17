"""Main FastAPI application for NCM Auth Service."""

from datetime import datetime

from auth_service.core.exceptions import BaseAPIException
from auth_service.domains.user.api.endpoints import router as user_router
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from ncm_foundation import (CacheManager, CorrelationIDMiddleware,
                            DatabaseManager, HealthCheckManager, Settings,
                            get_logger, setup_logging)

# Setup logging
settings = Settings()
setup_logging(settings.log_level, settings.log_format)
logger = get_logger(__name__)

# Initialize foundation services
db_manager = DatabaseManager(settings)
cache_manager = CacheManager(settings)
health_checker = HealthCheckManager(db_manager, cache_manager)

app = FastAPI(
    title="NCM Auth Service",
    version="0.1.0",
    description="Authentication and Authorization Service for NCM"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add correlation ID middleware
app.add_middleware(CorrelationIDMiddleware)

# Include routers
app.include_router(user_router, prefix="/api/v1/users", tags=["users"])
# TODO: Implement organization domain
# app.include_router(org_router, prefix="/api/v1/organizations", tags=["organizations"])


# Error handlers
@app.exception_handler(BaseAPIException)
async def api_exception_handler(request: Request, exc: BaseAPIException):
    """Handle custom API exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.detail,
                "timestamp": str(datetime.utcnow().isoformat())
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(
        f"Unhandled exception: {exc}",
        exc_info=True,
        extra={"path": request.url.path, "method": request.method}
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "timestamp": str(datetime.utcnow().isoformat())
            }
        }
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {"service": "NCM Auth Service", "version": "0.1.0"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return await health_checker.get_overall_health()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
