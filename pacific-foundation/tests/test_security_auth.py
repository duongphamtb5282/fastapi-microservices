"""Test cases for security authentication."""

import pytest
from unittest.mock import patch

from ncm_foundation.core.security.auth import JWTManager, PasswordManager


class TestPasswordManager:
    """Test PasswordManager functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.password_manager = PasswordManager()

    def test_password_hashing(self):
        """Test password hashing."""
        password = "test_password_123"
        hashed = self.password_manager.hash_password(password)

        assert hashed != password
        assert len(hashed) > 0

    def test_password_verification(self):
        """Test password verification."""
        password = "test_password_123"
        hashed = self.password_manager.hash_password(password)

        assert self.password_manager.verify_password(password, hashed) is True
        assert self.password_manager.verify_password("wrong_password", hashed) is False

    def test_password_hash_uniqueness(self):
        """Test that password hashes are unique."""
        password = "test_password_123"
        hash1 = self.password_manager.hash_password(password)
        hash2 = self.password_manager.hash_password(password)

        # Hashes should be different due to salt
        assert hash1 != hash2


class TestJWTManager:
    """Test JWTManager functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.jwt_manager = JWTManager(
            secret_key="test-secret-key",
            algorithm="HS256",
            access_token_expire_minutes=15
        )

    def test_jwt_creation(self):
        """Test JWT token creation."""
        payload = {"user_id": 123, "username": "testuser"}
        token = self.jwt_manager.create_access_token(payload)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_jwt_verification(self):
        """Test JWT token verification."""
        payload = {"user_id": 123, "username": "testuser"}
        token = self.jwt_manager.create_access_token(payload)

        decoded = self.jwt_manager.verify_token(token)
        assert decoded["user_id"] == 123
        assert decoded["username"] == "testuser"

    def test_jwt_invalid_token(self):
        """Test JWT verification with invalid token."""
        invalid_token = "invalid.jwt.token"

        with pytest.raises(Exception):
            self.jwt_manager.verify_token(invalid_token)

    def test_jwt_expired_token(self):
        """Test JWT verification with expired token."""
        # Create a JWT manager with very short expiration
        jwt_manager = JWTManager(
            secret_key="test-secret-key",
            algorithm="HS256",
            access_token_expire_minutes=0  # Expire immediately
        )

        payload = {"user_id": 123}
        token = jwt_manager.create_access_token(payload)

        # Token should be expired
        with pytest.raises(Exception):
            jwt_manager.verify_token(token)
