"""
Helper utility functions.
"""

import re
import uuid
from datetime import datetime
from typing import Any, Optional

from ncm_foundation.core.logging import logger


def generate_uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())


def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format a datetime object to string."""
    return dt.strftime(format_str)


def sanitize_string(text: str, max_length: Optional[int] = None) -> str:
    """Sanitize a string by removing dangerous characters and limiting length."""
    if not text:
        return ""

    # Remove potentially dangerous characters
    sanitized = re.sub(r'[<>"\']', "", text)

    # Limit length if specified
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
        logger.warning(
            "String truncated due to length limit",
            original_length=len(text),
            max_length=max_length,
        )

    return sanitized.strip()


def deep_merge_dicts(dict1: dict, dict2: dict) -> dict:
    """Deep merge two dictionaries."""
    result = dict1.copy()

    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dicts(result[key], value)
        else:
            result[key] = value

    return result


def chunk_list(lst: list, chunk_size: int) -> list:
    """Split a list into chunks of specified size."""
    for i in range(0, len(lst), chunk_size):
        yield lst[i : i + chunk_size]


def retry_on_exception(max_retries: int = 3, delay: float = 1.0):
    """Decorator to retry a function on exception."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"Attempt {attempt + 1} failed, retrying...",
                            error=str(e),
                            function=func.__name__,
                        )
                        import time

                        time.sleep(delay)
                    else:
                        logger.error(
                            f"All {max_retries} attempts failed",
                            error=str(e),
                            function=func.__name__,
                        )

            raise last_exception

        return wrapper

    return decorator
