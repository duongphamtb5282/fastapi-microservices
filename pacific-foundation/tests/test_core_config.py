"""Test cases for core configuration module."""

import os
import pytest
from unittest.mock import patch

from ncm_foundation.core.config import Settings, get_settings


class TestSettings:
    """Test Settings class functionality."""

    def test_settings_initialization(self):
        """Test that Settings can be initialized with default values."""
        settings = Settings()
        assert settings.app_name == "NCM Service"
        assert settings.app_version == "0.1.0"
        assert settings.debug is False
        assert settings.environment == "development"

    def test_settings_with_environment_variables(self):
        """Test that Settings reads from environment variables."""
        with patch.dict(os.environ, {
            "APP_NAME": "Test Service",
            "APP_VERSION": "1.0.0",
            "DEBUG": "true",
            "ENVIRONMENT": "production",
            "DATABASE_URL": "postgresql://test:test@localhost/test",
            "REDIS_URL": "redis://localhost:6379/1",
            "SECRET_KEY": "test-secret-key",
            "JWT_SECRET": "test-jwt-secret",
        }):
            settings = Settings()
            assert settings.app_name == "Test Service"
            assert settings.app_version == "1.0.0"
            assert settings.debug is True
            assert settings.environment == "production"
            assert "postgresql://test:test@localhost/test" in settings.database_url
            assert "redis://localhost:6379/1" in settings.redis_url

    def test_get_settings_singleton(self):
        """Test that get_settings returns a singleton instance."""
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2

    def test_environment_normalization(self):
        """Test that environment names are normalized."""
        with patch.dict(os.environ, {"ENVIRONMENT": "prod"}):
            settings = Settings()
            assert settings.environment == "production"

        with patch.dict(os.environ, {"ENVIRONMENT": "dev"}):
            settings = Settings()
            assert settings.environment == "development"

    def test_cors_origins_default(self):
        """Test that CORS origins has a default value."""
        settings = Settings()
        assert isinstance(settings.cors_origins, list)
        assert "http://localhost:3000" in settings.cors_origins


class TestConfigurationValidation:
    """Test configuration validation."""

    def test_required_fields_missing(self):
        """Test that required fields raise validation errors."""
        with patch.dict(os.environ, {}, clear=True):
            # Clear all environment variables
            with pytest.raises(Exception):  # Should raise validation error for missing required fields
                Settings()

    def test_database_url_required(self):
        """Test that database_url is required."""
        with patch.dict(os.environ, {"DATABASE_URL": ""}):
            with pytest.raises(Exception):
                Settings()

    def test_secret_keys_required(self):
        """Test that secret keys are required."""
        with patch.dict(os.environ, {
            "DATABASE_URL": "postgresql://test:test@localhost/test",
            "SECRET_KEY": "",
            "JWT_SECRET": "",
        }):
            with pytest.raises(Exception):
                Settings()
