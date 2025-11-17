"""Main application entry point."""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
# from ncm_foundation.core.config import FoundationConfig
from ncm_foundation.core.database.manager import DatabaseManager
from ncm_foundation.core.logging import LogManager, LogConfig, LogLevel
from ncm_foundation.core.middleware import CorrelationIDMiddleware
from ncm_sample.core.container import get_container
from ncm_sample.config.settings import get_settings
from ncm_sample.api.v1.router import create_v1_router
from ncm_sample.middlewares import CORSMiddleware, SecurityMiddleware, RateLimitMiddleware, AuthenticationMiddleware, GlobalErrorHandlingMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    # Database manager is already created in create_app and stored in app.state
    db_manager = app.state.db_manager

    # Load settings
    settings = get_settings()

    # Create log config from settings
    log_config = LogConfig(
        level=LogLevel(settings.log_level),
        format=settings.logging_format,
        handlers=["console", "file"] if settings.logging_file_path else [
            "console"],
        file_path=settings.logging_file_path or "logs/ncm-sample.log",
        max_file_size=settings.logging_max_file_size,
        max_files=settings.logging_max_files,
        enable_rotation=True,
        enable_masking=True
    )
    log_manager = LogManager(log_config)

    # Setup DI container
    container = get_container()
    container.register_instance(DatabaseManager, db_manager)
    container.register_instance(LogManager, log_manager)

    # Also register the database manager for the router
    from ncm_foundation.core.database.manager import DatabaseManager as DBManagerType
    container.register_instance(DBManagerType, db_manager)

    # Initialize Keycloak (optional, if configured)
    try:
        from ncm_sample.config.keycloak import get_keycloak_config
        keycloak_config = await get_keycloak_config()
        container.register_instance(type(keycloak_config), keycloak_config)
        print("  ✅ Keycloak initialized")
    except Exception as e:
        print(f"  ⚠️  Keycloak initialization failed: {e}")
        # Keycloak is optional, continue without it

    # Startup
    print(f"🚀 {settings.app_name} v{settings.app_version} starting...")
    print(f"📊 Environment: {settings.environment}")
    print(f"🔗 Database: {settings.database_url}")

    # Connect to database
    try:
        await db_manager.connect()
        print("  ✅ Database connected")
    except Exception as e:
        print(f"  ⚠️  Database connection failed: {e}")

    # Start logging
    await log_manager.start()
    print("  ✅ Logging started")

    yield  # Application runs here

    # Shutdown
    print("👋 Application shutting down...")

    # Disconnect from database
    try:
        await db_manager.disconnect()
        print("  ✅ Database disconnected")
    except Exception as e:
        print(f"  ⚠️  Database disconnection failed: {e}")

    # Stop logging
    await log_manager.stop()
    print("  ✅ Logging stopped")

    print("✅ Application shutdown complete")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    # Load settings
    settings = get_settings()

    # Create database config from settings
    from ncm_foundation.core.database.config import DatabaseConfig, DatabaseType
    from urllib.parse import urlparse

    # Parse database URL with proper validation
    parsed = urlparse(settings.database_url)

    # Validate and extract database URL components
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(
            f"Invalid DATABASE_URL format: {settings.database_url}")

    # Extract components with proper defaults
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    database = parsed.path.lstrip("/") if parsed.path else "ncm_sample_dev"
    username = parsed.username or "dev_user"
    password = parsed.password or "dev_password"

    # Validate required components
    if not database:
        raise ValueError("Database name is required in DATABASE_URL")

    # Create database config from parsed URL
    db_config = DatabaseConfig(
        db_type=settings.db_type,
        host=host,
        port=port,
        database=database,
        username=username,
        password=password,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_timeout=settings.database_pool_timeout,
        pool_recycle=settings.database_pool_recycle,
        echo=settings.database_echo
    )
    db_manager = DatabaseManager(db_config)
    print("  ✅ Database manager initialized")

    # Create FastAPI app with lifespan
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="NCM Sample Microservice with Foundation Library",
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/docs",  # Swagger UI
        redoc_url="/redoc",  # ReDoc
        openapi_url="/openapi.json",  # OpenAPI schema
    )

    # Add global error handling middleware (should be first to catch all errors)
    app.add_middleware(GlobalErrorHandlingMiddleware, debug=settings.debug)

    # Add CORS middleware
    cors_middleware = CORSMiddleware()
    app.add_middleware(
        cors_middleware.get_middleware(),
        allow_origins=cors_middleware.allow_origins,
        allow_credentials=cors_middleware.allow_credentials,
        allow_methods=cors_middleware.allow_methods,
        allow_headers=cors_middleware.allow_headers,
    )

    # Add correlation ID middleware
    app.add_middleware(CorrelationIDMiddleware)

    # Add security middleware
    security_middleware = SecurityMiddleware()
    app.add_middleware(security_middleware.get_middleware())

    # Store database manager in app state for router access
    app.state.db_manager = db_manager

    # Create and include routers (DI container is now available)
    from ncm_sample.api.v1.router import create_v1_router
    v1_router = create_v1_router(db_manager)
    app.include_router(v1_router)

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "version": settings.app_version,
            "environment": settings.environment
        }

    return app


# Create app instance
app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
