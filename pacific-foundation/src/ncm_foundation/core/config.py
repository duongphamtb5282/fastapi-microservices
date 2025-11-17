"""Configuration management for NCM Foundation."""

import os
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Application
    app_name: str = Field(default="NCM Service", env="APP_NAME")
    app_version: str = Field(default="0.1.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    environment: str = Field(default="development", env="ENVIRONMENT")

    # Database
    database_url: str = Field(..., env="DATABASE_URL")
    database_read_url: Optional[str] = Field(None, env="DATABASE_READ_URL")
    database_pool_size: int = Field(default=10, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, env="DATABASE_MAX_OVERFLOW")
    database_pool_recycle: int = Field(default=3600, env="DATABASE_POOL_RECYCLE")
    database_echo: bool = Field(default=False, env="DATABASE_ECHO")

    # Cache
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    cache_default_ttl: int = Field(default=3600, env="CACHE_DEFAULT_TTL")
    cache_max_connections: int = Field(default=10, env="CACHE_MAX_CONNECTIONS")

    # Security
    secret_key: str = Field(..., env="SECRET_KEY")
    jwt_secret: str = Field(..., env="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=1440, env="JWT_EXPIRE_MINUTES")

    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000"], env="CORS_ORIGINS"
    )

    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")

    # Monitoring
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance - lazy initialization
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the global settings instance, creating it if necessary."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# Alias for backward compatibility
FoundationConfig = Settings
