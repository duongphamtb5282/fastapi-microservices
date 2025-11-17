"""
Log masking implementation.
"""

import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Pattern

from .interfaces import LogMasker


class SensitiveDataMasker(LogMasker):
    """Sensitive data masker implementation."""

    def __init__(self):
        self.patterns: List[Pattern] = []
        self.replacements: List[str] = []
        self._setup_default_patterns()

    def _setup_default_patterns(self) -> None:
        """Setup default masking patterns."""
        # Credit card numbers
        self.add_pattern(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b", "[CARD]")

        # Email addresses
        self.add_pattern(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL]"
        )

        # Phone numbers
        self.add_pattern(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", "[PHONE]")

        # SSN
        self.add_pattern(r"\b\d{3}-\d{2}-\d{4}\b", "[SSN]")

        # Passwords (common patterns)
        self.add_pattern(
            r'password["\']?\s*[:=]\s*["\']?[^"\'\s]+["\']?', 'password="[MASKED]"'
        )

        # API keys
        self.add_pattern(
            r'api[_-]?key["\']?\s*[:=]\s*["\']?[A-Za-z0-9_-]+["\']?',
            'api_key="[MASKED]"',
        )

        # Tokens
        self.add_pattern(
            r'token["\']?\s*[:=]\s*["\']?[A-Za-z0-9._-]+["\']?', 'token="[MASKED]"'
        )

    def add_pattern(self, pattern: str, replacement: str) -> None:
        """Add masking pattern."""
        try:
            compiled_pattern = re.compile(pattern, re.IGNORECASE)
            self.patterns.append(compiled_pattern)
            self.replacements.append(replacement)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}")

    def remove_pattern(self, pattern: str) -> None:
        """Remove masking pattern."""
        try:
            compiled_pattern = re.compile(pattern, re.IGNORECASE)
            if compiled_pattern in self.patterns:
                index = self.patterns.index(compiled_pattern)
                self.patterns.pop(index)
                self.replacements.pop(index)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}")

    def mask_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mask sensitive data in dictionary."""
        if not isinstance(data, dict):
            return data

        masked_data = {}
        for key, value in data.items():
            if isinstance(value, str):
                masked_data[key] = self.mask_text(value)
            elif isinstance(value, dict):
                masked_data[key] = self.mask_sensitive_data(value)
            elif isinstance(value, list):
                masked_data[key] = [
                    (
                        self.mask_sensitive_data(item)
                        if isinstance(item, dict)
                        else self.mask_text(item) if isinstance(item, str) else item
                    )
                    for item in value
                ]
            else:
                masked_data[key] = value

        return masked_data

    def mask_text(self, text: str) -> str:
        """Mask sensitive data in text."""
        if not isinstance(text, str):
            return text

        masked_text = text
        for pattern, replacement in zip(self.patterns, self.replacements):
            masked_text = pattern.sub(replacement, masked_text)

        return masked_text


class CreditCardMasker(LogMasker):
    """Credit card specific masker."""

    def __init__(self):
        self.patterns = [
            re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"),
            re.compile(r"\b\d{13,19}\b"),  # Raw numbers
        ]
        self.replacement = "[CARD]"

    def add_pattern(self, pattern: str, replacement: str) -> None:
        """Add pattern (not used in this implementation)."""
        pass

    def remove_pattern(self, pattern: str) -> None:
        """Remove pattern (not used in this implementation)."""
        pass

    def mask_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mask credit card data in dictionary."""
        if not isinstance(data, dict):
            return data

        masked_data = {}
        for key, value in data.items():
            if isinstance(value, str):
                masked_data[key] = self.mask_text(value)
            elif isinstance(value, dict):
                masked_data[key] = self.mask_sensitive_data(value)
            elif isinstance(value, list):
                masked_data[key] = [
                    (
                        self.mask_sensitive_data(item)
                        if isinstance(item, dict)
                        else self.mask_text(item) if isinstance(item, str) else item
                    )
                    for item in value
                ]
            else:
                masked_data[key] = value

        return masked_data

    def mask_text(self, text: str) -> str:
        """Mask credit card numbers in text."""
        if not isinstance(text, str):
            return text

        masked_text = text
        for pattern in self.patterns:
            masked_text = pattern.sub(self.replacement, masked_text)

        return masked_text


class EmailMasker(LogMasker):
    """Email specific masker."""

    def __init__(self):
        self.pattern = re.compile(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        )
        self.replacement = "[EMAIL]"

    def add_pattern(self, pattern: str, replacement: str) -> None:
        """Add pattern (not used in this implementation)."""
        pass

    def remove_pattern(self, pattern: str) -> None:
        """Remove pattern (not used in this implementation)."""
        pass

    def mask_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mask email addresses in dictionary."""
        if not isinstance(data, dict):
            return data

        masked_data = {}
        for key, value in data.items():
            if isinstance(value, str):
                masked_data[key] = self.mask_text(value)
            elif isinstance(value, dict):
                masked_data[key] = self.mask_sensitive_data(value)
            elif isinstance(value, list):
                masked_data[key] = [
                    (
                        self.mask_sensitive_data(item)
                        if isinstance(item, dict)
                        else self.mask_text(item) if isinstance(item, str) else item
                    )
                    for item in value
                ]
            else:
                masked_data[key] = value

        return masked_data

    def mask_text(self, text: str) -> str:
        """Mask email addresses in text."""
        if not isinstance(text, str):
            return text

        return self.pattern.sub(self.replacement, text)
