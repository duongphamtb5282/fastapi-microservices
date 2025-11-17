"""
Validation utility functions.
"""

import re
from typing import Optional
from urllib.parse import urlparse

from ncm_foundation.core.logging import logger


def validate_email(email: str) -> bool:
    """Validate email address format."""
    if not email:
        return False

    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    is_valid = bool(re.match(pattern, email))

    if not is_valid:
        logger.debug("Invalid email format", email=email)

    return is_valid


def validate_phone(phone: str) -> bool:
    """Validate phone number format."""
    if not phone:
        return False

    # Remove all non-digit characters
    digits_only = re.sub(r"\D", "", phone)

    # Check if it's a valid length (7-15 digits)
    is_valid = 7 <= len(digits_only) <= 15

    if not is_valid:
        logger.debug("Invalid phone format", phone=phone, digits_count=len(digits_only))

    return is_valid


def validate_url(url: str) -> bool:
    """Validate URL format."""
    if not url:
        return False

    try:
        result = urlparse(url)
        is_valid = all([result.scheme, result.netloc])

        if not is_valid:
            logger.debug("Invalid URL format", url=url)

        return is_valid
    except Exception as e:
        logger.debug("URL validation error", url=url, error=str(e))
        return False


def validate_uuid(uuid_string: str) -> bool:
    """Validate UUID format."""
    if not uuid_string:
        return False

    pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    is_valid = bool(re.match(pattern, uuid_string, re.IGNORECASE))

    if not is_valid:
        logger.debug("Invalid UUID format", uuid=uuid_string)

    return is_valid


def validate_password_strength(password: str, min_length: int = 8) -> dict:
    """Validate password strength."""
    if not password:
        return {"is_valid": False, "score": 0, "feedback": ["Password is required"]}

    score = 0
    feedback = []

    if len(password) >= min_length:
        score += 1
    else:
        feedback.append(f"Password must be at least {min_length} characters long")

    if re.search(r"[A-Z]", password):
        score += 1
    else:
        feedback.append("Password must contain at least one uppercase letter")

    if re.search(r"[a-z]", password):
        score += 1
    else:
        feedback.append("Password must contain at least one lowercase letter")

    if re.search(r"\d", password):
        score += 1
    else:
        feedback.append("Password must contain at least one digit")

    if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        score += 1
    else:
        feedback.append("Password must contain at least one special character")

    is_valid = score >= 4

    return {"is_valid": is_valid, "score": score, "max_score": 5, "feedback": feedback}
