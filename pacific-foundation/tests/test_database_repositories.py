"""Test cases for database repositories."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from ncm_foundation.core.database.repositories.sqlalchemy_repo import SQLAlchemyRepository
from ncm_foundation.core.database.models.base import BaseModel
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base


# Test models
TestBase = declarative_base()

class TestModel(BaseModel, TestBase):
    __tablename__ = "test_models"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500))


class TestRepository(SQLAlchemyRepository[TestModel]):
    """Test repository implementation."""

    def __init__(self, session):
        super().__init__(TestModel, session)


class TestSQLAlchemyRepository:
    """Test SQLAlchemyRepository functionality."""

    @pytest.mark.asyncio
    async def test_repository_initialization(self):
        """Test repository can be initialized."""
        mock_session = MagicMock()
        repo = TestRepository(mock_session)

        assert repo.model_class == TestModel
        assert repo.session == mock_session

    @pytest.mark.asyncio
    async def test_create_entity(self):
        """Test creating an entity."""
        mock_session = MagicMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        repo = TestRepository(mock_session)

        test_data = {"name": "Test Entity", "description": "Test Description"}
        result = await repo.create(test_data)

        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id(self):
        """Test getting entity by ID."""
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = TestModel(id=1, name="Test", description="Test")
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = TestRepository(mock_session)

        entity = await repo.get_by_id(1)
        assert entity is not None
        assert entity.id == 1

    @pytest.mark.asyncio
    async def test_get_by_field(self):
        """Test getting entity by field."""
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = TestModel(id=1, name="Test", description="Test")
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = TestRepository(mock_session)

        entity = await repo.get_by_field("name", "Test")
        assert entity is not None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_entities(self):
        """Test listing entities."""
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            TestModel(id=1, name="Test1", description="Test1"),
            TestModel(id=2, name="Test2", description="Test2")
        ]
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = TestRepository(mock_session)

        entities = await repo.list()
        assert len(entities) == 2

    @pytest.mark.asyncio
    async def test_update_entity(self):
        """Test updating an entity."""
        # Mock the get_by_id call
        mock_session = MagicMock()
        mock_session.execute = AsyncMock()

        # Mock existing entity
        existing_entity = TestModel(id=1, name="Old Name", description="Old Description")
        mock_session.execute.return_value.scalar_one_or_none.return_value = existing_entity

        # Mock commit and refresh
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        repo = TestRepository(mock_session)

        updated = await repo.update(1, {"name": "New Name"})
        assert updated is not None

    @pytest.mark.asyncio
    async def test_delete_entity(self):
        """Test deleting an entity."""
        mock_session = MagicMock()
        mock_session.execute = AsyncMock()
        mock_session.delete = MagicMock()
        mock_session.commit = AsyncMock()

        # Mock existing entity
        existing_entity = TestModel(id=1, name="Test", description="Test")
        mock_session.execute.return_value.scalar_one_or_none.return_value = existing_entity

        repo = TestRepository(mock_session)

        success = await repo.delete(1)
        assert success is True
        mock_session.delete.assert_called_once()
        mock_session.commit.assert_called_once()
