"""
Database configuration module.
"""

from enum import Enum
from typing import Any, Dict, Optional

try:
    from pydantic import BaseSettings
except ImportError:
    from pydantic_settings import BaseSettings

from pydantic import Field


class DatabaseType(Enum):
    """Supported database types."""

    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    MONGODB = "mongodb"
    NEO4J = "neo4j"  # GraphDB support


class DatabaseConfig:
    """Database configuration class."""

    def __init__(
        self,
        db_type: DatabaseType,
        host: str = "localhost",
        port: int = 5432,
        database: str = "ncm",
        username: str = "postgres",
        password: str = "",
        pool_size: int = 10,
        max_overflow: int = 20,
        pool_timeout: int = 30,
        pool_recycle: int = 3600,
        pool_pre_ping: bool = True,
        echo: bool = False,
        security_enabled: bool = False,
        encryption_key: Optional[str] = None,
        rls_enabled: bool = False,
        **kwargs,
    ):
        self.db_type = db_type
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        self.pool_pre_ping = pool_pre_ping
        self.echo = echo
        self.security_enabled = security_enabled
        self.encryption_key = encryption_key
        self.rls_enabled = rls_enabled
        self.extra_params = kwargs


class DatabaseSettings(BaseSettings):
    """Database configuration settings using Pydantic."""

    # Database connection
    db_type: DatabaseType = Field(default=DatabaseType.POSTGRESQL)
    host: str = Field(default="localhost")
    port: int = Field(default=5432)
    database: str = Field(default="ncm")
    username: str = Field(default="postgres")
    password: str = Field(default="")

    # Connection pooling
    pool_size: int = Field(default=10)
    max_overflow: int = Field(default=20)
    pool_timeout: int = Field(default=30)
    pool_recycle: int = Field(default=3600)
    pool_pre_ping: bool = Field(default=True)

    # Security
    security_enabled: bool = Field(default=False)
    encryption_key: Optional[str] = Field(default=None)
    rls_enabled: bool = Field(default=False)

    # Monitoring
    echo: bool = Field(default=False)
    echo_pool: bool = Field(default=False)

    class Config:
        env_prefix = "DB_"
        case_sensitive = False
