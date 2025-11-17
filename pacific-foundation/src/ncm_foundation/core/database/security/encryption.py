"""
Field encryption for database security.
"""

import base64
import logging
from typing import Any, Optional

from cryptography.fernet import Fernet
from sqlalchemy import String, Text, TypeDecorator
from sqlalchemy.types import TypeDecorator

logger = logging.getLogger(__name__)


class EncryptedString(TypeDecorator):
    """Encrypted string field type for SQLAlchemy."""

    impl = String
    cache_ok = True

    def __init__(self, encryption_key: Optional[str] = None, *args, **kwargs):
        self.encryption_key = encryption_key or self._get_default_key()
        try:
            self.cipher = Fernet(self.encryption_key.encode())
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            raise
        super().__init__(*args, **kwargs)

    def process_bind_param(self, value: Any, dialect) -> Optional[str]:
        """Encrypt value before storing."""
        if value is not None:
            try:
                encrypted = self.cipher.encrypt(str(value).encode())
                return base64.b64encode(encrypted).decode()
            except Exception as e:
                logger.error(f"Failed to encrypt value: {e}")
                raise
        return value

    def process_result_value(self, value: Any, dialect) -> Optional[str]:
        """Decrypt value after retrieving."""
        if value is not None:
            try:
                encrypted = base64.b64decode(value.encode())
                return self.cipher.decrypt(encrypted).decode()
            except Exception as e:
                logger.error(f"Failed to decrypt value: {e}")
                raise
        return value

    def _get_default_key(self) -> str:
        """Get default encryption key."""
        # In production, this should come from secure key management
        return Fernet.generate_key().decode()


class EncryptedText(TypeDecorator):
    """Encrypted text field type for SQLAlchemy."""

    impl = Text
    cache_ok = True

    def __init__(self, encryption_key: Optional[str] = None, *args, **kwargs):
        self.encryption_key = encryption_key or self._get_default_key()
        try:
            self.cipher = Fernet(self.encryption_key.encode())
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            raise
        super().__init__(*args, **kwargs)

    def process_bind_param(self, value: Any, dialect) -> Optional[str]:
        """Encrypt value before storing."""
        if value is not None:
            try:
                encrypted = self.cipher.encrypt(str(value).encode())
                return base64.b64encode(encrypted).decode()
            except Exception as e:
                logger.error(f"Failed to encrypt value: {e}")
                raise
        return value

    def process_result_value(self, value: Any, dialect) -> Optional[str]:
        """Decrypt value after retrieving."""
        if value is not None:
            try:
                encrypted = base64.b64decode(value.encode())
                return self.cipher.decrypt(encrypted).decode()
            except Exception as e:
                logger.error(f"Failed to decrypt value: {e}")
                raise
        return value

    def _get_default_key(self) -> str:
        """Get default encryption key."""
        return Fernet.generate_key().decode()


class EncryptionManager:
    """Encryption manager for database fields."""

    def __init__(self, master_key: Optional[str] = None):
        self.master_key = master_key or Fernet.generate_key().decode()
        self.cipher = Fernet(self.master_key.encode())
        self._field_keys: dict = {}

    def generate_field_key(self, field_name: str) -> str:
        """Generate encryption key for specific field."""
        if field_name not in self._field_keys:
            self._field_keys[field_name] = Fernet.generate_key().decode()
        return self._field_keys[field_name]

    def encrypt_value(self, value: str, field_name: Optional[str] = None) -> str:
        """Encrypt a value."""
        if field_name and field_name in self._field_keys:
            cipher = Fernet(self._field_keys[field_name].encode())
        else:
            cipher = self.cipher

        encrypted = cipher.encrypt(str(value).encode())
        return base64.b64encode(encrypted).decode()

    def decrypt_value(
        self, encrypted_value: str, field_name: Optional[str] = None
    ) -> str:
        """Decrypt a value."""
        if field_name and field_name in self._field_keys:
            cipher = Fernet(self._field_keys[field_name].encode())
        else:
            cipher = self.cipher

        encrypted = base64.b64decode(encrypted_value.encode())
        return cipher.decrypt(encrypted).decode()

    def rotate_key(self, field_name: str) -> str:
        """Rotate encryption key for a field."""
        old_key = self._field_keys.get(field_name)
        new_key = Fernet.generate_key().decode()
        self._field_keys[field_name] = new_key
        return old_key
