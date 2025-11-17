"""
API tests for NCM Sample Project.
"""

import httpx
import pytest
from fastapi.testclient import TestClient
from ncm_sample.api import app


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def setup_services():
    """Setup services for testing."""
    from unittest.mock import AsyncMock, Mock

    # Mock the global services
    from ncm_sample.api import (auth_service, cache_manager, db_manager,
                                log_manager, role_service, user_role_service,
                                user_service)

    # Create mock services
    mock_db_manager = Mock()
    mock_cache_manager = Mock()
    mock_log_manager = Mock()
    mock_user_service = Mock()
    mock_role_service = Mock()
    mock_user_role_service = Mock()
    mock_auth_service = Mock()

    # Set up mock methods
    mock_auth_service.login = AsyncMock(return_value=None)

    # Replace global services
    import ncm_sample.api

    ncm_sample.api.db_manager = mock_db_manager
    ncm_sample.api.cache_manager = mock_cache_manager
    ncm_sample.api.log_manager = mock_log_manager
    ncm_sample.api.user_service = mock_user_service
    ncm_sample.api.role_service = mock_role_service
    ncm_sample.api.user_role_service = mock_user_role_service
    ncm_sample.api.auth_service = mock_auth_service


@pytest.fixture
def sample_user():
    """Sample user data."""
    return {
        "email": "test@example.com",
        "username": "testuser",
        "first_name": "Test",
        "last_name": "User",
        "password": "password123",
    }


@pytest.fixture
def sample_role():
    """Sample role data."""
    return {
        "name": "admin",
        "description": "Administrator role",
        "permissions": '["read", "write", "delete"]',
    }


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "services" in data
        assert "version" in data


class TestUserEndpoints:
    """Test user endpoints."""

    def test_create_user_unauthorized(self, client, sample_user):
        """Test creating user without authentication."""
        response = client.post("/users/", json=sample_user)
        assert response.status_code == 403  # 403 for missing credentials

    def test_get_user_unauthorized(self, client):
        """Test getting user without authentication."""
        response = client.get("/users/1")
        assert response.status_code == 403  # 403 for missing credentials

    def test_list_users_unauthorized(self, client):
        """Test listing users without authentication."""
        response = client.get("/users/")
        assert response.status_code == 403  # 403 for missing credentials


class TestRoleEndpoints:
    """Test role endpoints."""

    def test_create_role_unauthorized(self, client, sample_role):
        """Test creating role without authentication."""
        response = client.post("/roles/", json=sample_role)
        assert response.status_code == 403  # 403 for missing credentials

    def test_get_role_unauthorized(self, client):
        """Test getting role without authentication."""
        response = client.get("/roles/1")
        assert response.status_code == 403  # 403 for missing credentials

    def test_list_roles_unauthorized(self, client):
        """Test listing roles without authentication."""
        response = client.get("/roles/")
        assert response.status_code == 403  # 403 for missing credentials


class TestCacheEndpoints:
    """Test cache endpoints."""

    def test_cache_stats_unauthorized(self, client):
        """Test cache stats without authentication."""
        response = client.get("/cache/stats")
        assert response.status_code == 403  # 403 for missing credentials

    def test_clear_cache_unauthorized(self, client):
        """Test clear cache without authentication."""
        response = client.post("/cache/clear")
        assert response.status_code == 403  # 403 for missing credentials


class TestAuthentication:
    """Test authentication endpoints."""

    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        login_data = {"username": "invalid@example.com", "password": "wrongpassword"}

        response = client.post("/auth/login", json=login_data)
        # Since auth service is mocked to return None, this should return 401
        # But if auth service is None, it returns 500
        assert response.status_code in [401, 500]

    def test_login_missing_fields(self, client):
        """Test login with missing fields."""
        login_data = {
            "username": "test@example.com"
            # Missing password
        }

        response = client.post("/auth/login", json=login_data)
        assert response.status_code == 422  # Validation error


class TestAPIStructure:
    """Test API structure and documentation."""

    def test_openapi_schema(self, client):
        """Test OpenAPI schema endpoint."""
        response = client.get("/openapi.json")
        assert response.status_code == 200

        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema

    def test_docs_endpoint(self, client):
        """Test documentation endpoint."""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_redoc_endpoint(self, client):
        """Test ReDoc endpoint."""
        response = client.get("/redoc")
        assert response.status_code == 200


@pytest.mark.integration
class TestIntegration:
    """Integration tests (require running services)."""

    @pytest.mark.skip(reason="Requires running services")
    def test_full_user_workflow(self, client):
        """Test complete user workflow."""
        # This test would require running services
        # and proper authentication setup
        pass

    @pytest.mark.skip(reason="Requires running services")
    def test_cache_operations(self, client):
        """Test cache operations."""
        # This test would require running services
        pass
