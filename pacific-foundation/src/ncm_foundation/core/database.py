"""Database management and connection pooling."""

import logging
from contextlib import asynccontextmanager
from typing import Generator, Optional

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from .config import get_settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Database connection manager with connection pooling."""

    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        self._read_engine: Optional[Engine] = None
        self._write_engine: Optional[Engine] = None
        self._read_session_factory: Optional[sessionmaker] = None
        self._write_session_factory: Optional[sessionmaker] = None

    def get_read_engine(self) -> Engine:
        """Get read-only database engine with connection pooling."""
        if not self._read_engine:
            self._read_engine = create_engine(
                self.settings.database_read_url or self.settings.database_url,
                poolclass=QueuePool,
                pool_size=self.settings.database_pool_size,
                max_overflow=self.settings.database_max_overflow,
                pool_pre_ping=True,
                pool_recycle=self.settings.database_pool_recycle,
                echo=self.settings.database_echo,
                connect_args={
                    "options": "-c timezone=utc",
                    "application_name": "ncm_read",
                },
            )
        return self._read_engine

    def get_write_engine(self) -> Engine:
        """Get read-write database engine with connection pooling."""
        if not self._write_engine:
            self._write_engine = create_engine(
                self.settings.database_url,
                poolclass=QueuePool,
                pool_size=self.settings.database_pool_size,
                max_overflow=self.settings.database_max_overflow,
                pool_pre_ping=True,
                pool_recycle=self.settings.database_pool_recycle,
                echo=self.settings.database_echo,
                connect_args={
                    "options": "-c timezone=utc",
                    "application_name": "ncm_write",
                },
            )
        return self._write_engine

    def get_read_session_factory(self) -> sessionmaker:
        """Get read-only session factory."""
        if not self._read_session_factory:
            self._read_session_factory = sessionmaker(
                bind=self.get_read_engine(),
                class_=Session,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False,
            )
        return self._read_session_factory

    def get_write_session_factory(self) -> sessionmaker:
        """Get read-write session factory."""
        if not self._write_session_factory:
            self._write_session_factory = sessionmaker(
                bind=self.get_write_engine(),
                class_=Session,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False,
            )
        return self._write_session_factory

    @asynccontextmanager
    async def get_read_session(self) -> Generator[Session, None, None]:
        """Get read-only database session with proper cleanup."""
        session = self.get_read_session_factory()()
        try:
            yield session
        except Exception as e:
            logger.error(f"Read session error: {e}")
            session.rollback()
            raise
        finally:
            session.close()

    @asynccontextmanager
    async def get_write_session(self) -> Generator[Session, None, None]:
        """Get read-write database session with proper cleanup."""
        session = self.get_write_session_factory()()
        try:
            yield session
        except Exception as e:
            logger.error(f"Write session error: {e}")
            session.rollback()
            raise
        finally:
            session.close()

    async def health_check(self) -> bool:
        """Check database connection health."""
        try:
            with self.get_read_engine().connect() as conn:
                conn.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
