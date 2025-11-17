"""
Configuration for NCM Sample Project.
"""

from typing import List, Optional

from ncm_foundation.core.config import FoundationConfig, get_settings


class Settings(FoundationConfig):
    """Application settings extending FoundationConfig."""

    # Kafka settings
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic_prefix: str = "ncm.sample"

    # Keycloak settings (replaces OpenAM)
    keycloak_server_url: str = "http://localhost:8080"
    keycloak_realm: str = "master"
    keycloak_client_id: str = "ncm-sample-client"
    keycloak_client_secret: str = "your-client-secret"
    keycloak_admin_username: str = "admin"
    keycloak_admin_password: str = "admin-password"

    # Legacy OpenAM settings (for backward compatibility)
    openam_url: str = "http://localhost:8080/openam"
    openam_realm: str = "/"
    openam_admin_user: str = "amAdmin"
    openam_admin_password: str = "password"

    # Service discovery
    service_discovery_enabled: bool = True
    consul_url: str = "http://localhost:8500"

    # Feature flags
    enable_audit_logging: bool = True
    enable_metrics: bool = True
    enable_circuit_breaker: bool = True
    enable_rate_limiting: bool = True

    # API settings
    api_prefix: str = "/api/v1"
    api_rate_limit_per_minute: int = 100
    api_rate_limit_burst: int = 10

    # Migration settings
    alembic_config_path: str = "alembic.ini"
    migration_directory: str = "migrations"

    # Health check settings
    health_check_timeout: int = 30
    health_check_services: List[str] = ["database", "cache", "messaging"]

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance using foundation's get_settings
settings = get_settings()
