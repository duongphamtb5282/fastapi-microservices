"""
JSON encoders for custom data types.
"""

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from ncm_foundation.core.logging import logger


class JSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for common data types."""

    def default(self, obj: Any) -> Any:
        """Convert objects to JSON-serializable format."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, date):
            return obj.isoformat()
        elif isinstance(obj, UUID):
            return str(obj)
        elif isinstance(obj, Decimal):
            return float(obj)
        elif hasattr(obj, "model_dump"):
            # Pydantic model
            return obj.model_dump()
        elif hasattr(obj, "dict"):
            # Pydantic v1 model
            return obj.dict()
        elif hasattr(obj, "__dict__"):
            # Generic object with __dict__
            return obj.__dict__
        else:
            logger.warning("Unable to serialize object", obj_type=type(obj).__name__)
            return str(obj)


class CustomJSONEncoder(JSONEncoder):
    """Extended JSON encoder with additional custom types."""

    def default(self, obj: Any) -> Any:
        """Convert objects to JSON-serializable format with additional types."""
        # Try the parent encoder first
        try:
            return super().default(obj)
        except TypeError:
            pass

        # Handle additional custom types
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        elif hasattr(obj, "to_json"):
            return obj.to_json()
        else:
            logger.warning(
                "Unable to serialize custom object", obj_type=type(obj).__name__
            )
            return str(obj)


def safe_json_dumps(obj: Any, **kwargs) -> str:
    """Safely serialize an object to JSON string."""
    try:
        return json.dumps(obj, cls=CustomJSONEncoder, **kwargs)
    except Exception as e:
        logger.error(
            "JSON serialization failed", error=str(e), obj_type=type(obj).__name__
        )
        return json.dumps({"error": "Serialization failed", "type": type(obj).__name__})


def safe_json_loads(json_str: str, **kwargs) -> Any:
    """Safely deserialize a JSON string to object."""
    try:
        return json.loads(json_str, **kwargs)
    except Exception as e:
        logger.error("JSON deserialization failed", error=str(e))
        return None
