"""Application settings with environment-specific configuration."""

import os
from typing import List, Literal
from pydantic_settings import BaseSettings
from pydantic import Field
from pydantic import model_validator
from ncm_foundation.core.database.config import DatabaseType


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    # Environment
    environment: Literal["development", "production"] = Field(
        default="development")
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")
    db_type: DatabaseType = Field(default=DatabaseType.POSTGRESQL)

    # Application
    app_name: str = Field(default="NCM Sample")
    app_version: str = Field(default="1.0.0")

    # Logging (for ncm_foundation compatibility)
    logging_level: str = Field(default="INFO", env="LOG_LEVEL")
    logging_format: str = Field(default="json", env="LOG_FORMAT")
    logging_file_path: str = Field(default="", env="LOG_FILE_PATH")
    logging_max_file_size: int = Field(
        default=10485760, env="LOG_MAX_FILE_SIZE")
    logging_max_files: int = Field(default=10, env="LOG_MAX_FILES")

    # Database (for ncm_foundation compatibility)
    database_url: str = Field(..., env="DATABASE_URL")
    database_read_url: str = Field(default="", env="DATABASE_READ_URL")
    database_pool_size: int = Field(default=10, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, env="DATABASE_MAX_OVERFLOW")
    database_pool_timeout: int = Field(default=30, env="DATABASE_POOL_TIMEOUT")
    database_pool_recycle: int = Field(
        default=3600, env="DATABASE_POOL_RECYCLE")
    database_echo: bool = Field(default=False, env="DATABASE_ECHO")

    # Keycloak
    keycloak_server_url: str = Field(..., env="KEYCLOAK_SERVER_URL")
    keycloak_realm_name: str = Field(..., env="KEYCLOAK_REALM_NAME")
    keycloak_client_id: str = Field(..., env="KEYCLOAK_CLIENT_ID")
    keycloak_client_secret: str = Field(..., env="KEYCLOAK_CLIENT_SECRET")
    keycloak_admin_username: str = Field(..., env="KEYCLOAK_ADMIN_USERNAME")
    keycloak_admin_password: str = Field(..., env="KEYCLOAK_ADMIN_PASSWORD")

    # JWT
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=1440, env="JWT_EXPIRE_MINUTES")
    jwt_refresh_expire_days: int = Field(default=7, env="JWT_REFRESH_EXPIRE_DAYS")

    # Kafka
    kafka_bootstrap_servers: str = Field(..., env="KAFKA_BOOTSTRAP_SERVERS")
    kafka_group_id: str = Field(..., env="KAFKA_GROUP_ID")
    kafka_auto_offset_reset: str = Field(
        default="earliest", env="KAFKA_AUTO_OFFSET_RESET")

    # Redis
    redis_url: str = Field(..., env="REDIS_URL")
    cache_default_ttl: int = Field(default=300, env="CACHE_DEFAULT_TTL")
    cache_max_connections: int = Field(default=20, env="CACHE_MAX_CONNECTIONS")
    cache_serialization_type: str = Field(default="json", env="CACHE_SERIALIZATION_TYPE")
    cache_enable_reloader: bool = Field(default=True, env="CACHE_ENABLE_RELOADER")

    # Security
    secret_key: str = Field(..., env="SECRET_KEY")
    jwt_secret: str = Field(..., env="JWT_SECRET")

    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000"], env="CORS_ORIGINS")

    # Elasticsearch
    elasticsearch_url: str = Field(default="", env="ELASTICSEARCH_URL")
    elasticsearch_index: str = Field(
        default="ncm-sample", env="ELASTICSEARCH_INDEX")

    class Config:
        env_file = f".env.{os.getenv('ENVIRONMENT', 'dev')}"
        case_sensitive = False

    @model_validator(mode='before')
    def _normalize_environment(cls, values):
        """Allow short environment names in ENVIRONMENT (e.g. 'dev'/'prod').

        This runs before validation and maps common short names to the
        canonical literals expected by the model.
        """
        env = os.getenv('ENVIRONMENT') or values.get('environment')
        if isinstance(env, str):
            env_lower = env.lower()
            if env_lower in ('dev', 'development'):
                values['environment'] = 'development'
            elif env_lower in ('prod', 'production'):
                values['environment'] = 'production'
        return values


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
