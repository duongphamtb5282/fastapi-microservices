"""
Cache serialization module for ncm-foundation.

This module provides various serialization methods for cache data including:
- JSON serialization
- Pickle serialization
- MessagePack serialization
- Custom serializers
- Compression support
"""

import json
import logging
import pickle
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Optional, Union

try:
    import msgpack

    MSGPACK_AVAILABLE = True
except ImportError:
    MSGPACK_AVAILABLE = False

try:
    import orjson

    ORJSON_AVAILABLE = True
except ImportError:
    ORJSON_AVAILABLE = False

logger = logging.getLogger(__name__)


class SerializationType(Enum):
    """Serialization type enumeration."""

    JSON = "json"
    PICKLE = "pickle"
    MSGPACK = "msgpack"
    ORJSON = "orjson"
    CUSTOM = "custom"


class CompressionType(Enum):
    """Compression type enumeration."""

    NONE = "none"
    GZIP = "gzip"
    LZ4 = "lz4"
    ZSTD = "zstd"


class CacheSerializer(ABC):
    """Abstract cache serializer interface."""

    @abstractmethod
    def serialize(self, value: Any) -> bytes:
        """Serialize value for storage."""
        pass

    @abstractmethod
    def deserialize(self, data: bytes) -> Any:
        """Deserialize value from storage."""
        pass

    @abstractmethod
    def get_size(self, value: Any) -> int:
        """Get serialized size of value."""
        pass


class JSONSerializer(CacheSerializer):
    """JSON-based cache serializer."""

    def __init__(self, ensure_ascii: bool = False, separators: tuple = (",", ":")):
        self.ensure_ascii = ensure_ascii
        self.separators = separators

    def serialize(self, value: Any) -> bytes:
        """Serialize value to JSON bytes."""
        try:
            return json.dumps(
                value,
                ensure_ascii=self.ensure_ascii,
                separators=self.separators,
                default=str,
            ).encode("utf-8")
        except Exception as e:
            logger.error(f"JSON serialization failed: {e}")
            raise

    def deserialize(self, data: bytes) -> Any:
        """Deserialize JSON bytes to value."""
        try:
            return json.loads(data.decode("utf-8"))
        except Exception as e:
            logger.error(f"JSON deserialization failed: {e}")
            raise

    def get_size(self, value: Any) -> int:
        """Get JSON serialized size."""
        try:
            return len(self.serialize(value))
        except Exception:
            return 0


class ORJSONSerializer(CacheSerializer):
    """ORJSON-based cache serializer (faster than standard JSON)."""

    def __init__(self, option: int = 0):
        if not ORJSON_AVAILABLE:
            raise ImportError(
                "orjson is not available. Install with: pip install orjson"
            )
        self.option = option

    def serialize(self, value: Any) -> bytes:
        """Serialize value to ORJSON bytes."""
        try:
            return orjson.dumps(value, option=self.option)
        except Exception as e:
            logger.error(f"ORJSON serialization failed: {e}")
            raise

    def deserialize(self, data: bytes) -> Any:
        """Deserialize ORJSON bytes to value."""
        try:
            return orjson.loads(data)
        except Exception as e:
            logger.error(f"ORJSON deserialization failed: {e}")
            raise

    def get_size(self, value: Any) -> int:
        """Get ORJSON serialized size."""
        try:
            return len(self.serialize(value))
        except Exception:
            return 0


class PickleSerializer(CacheSerializer):
    """Pickle-based cache serializer."""

    def __init__(self, protocol: int = pickle.HIGHEST_PROTOCOL):
        self.protocol = protocol

    def serialize(self, value: Any) -> bytes:
        """Serialize value to pickle bytes."""
        try:
            return pickle.dumps(value, protocol=self.protocol)
        except Exception as e:
            logger.error(f"Pickle serialization failed: {e}")
            raise

    def deserialize(self, data: bytes) -> Any:
        """Deserialize pickle bytes to value."""
        try:
            return pickle.loads(data)
        except Exception as e:
            logger.error(f"Pickle deserialization failed: {e}")
            raise

    def get_size(self, value: Any) -> int:
        """Get pickle serialized size."""
        try:
            return len(self.serialize(value))
        except Exception:
            return 0


class MessagePackSerializer(CacheSerializer):
    """MessagePack-based cache serializer."""

    def __init__(self, use_bin_type: bool = True):
        if not MSGPACK_AVAILABLE:
            raise ImportError(
                "msgpack is not available. Install with: pip install msgpack"
            )
        self.use_bin_type = use_bin_type

    def serialize(self, value: Any) -> bytes:
        """Serialize value to MessagePack bytes."""
        try:
            return msgpack.packb(value, use_bin_type=self.use_bin_type)
        except Exception as e:
            logger.error(f"MessagePack serialization failed: {e}")
            raise

    def deserialize(self, data: bytes) -> Any:
        """Deserialize MessagePack bytes to value."""
        try:
            return msgpack.unpackb(data, raw=False)
        except Exception as e:
            logger.error(f"MessagePack deserialization failed: {e}")
            raise

    def get_size(self, value: Any) -> int:
        """Get MessagePack serialized size."""
        try:
            return len(self.serialize(value))
        except Exception:
            return 0


class CompressedSerializer(CacheSerializer):
    """Compressed cache serializer wrapper."""

    def __init__(
        self,
        serializer: CacheSerializer,
        compression_type: CompressionType = CompressionType.GZIP,
        compression_level: int = 6,
        min_size: int = 1024,
    ):
        self.serializer = serializer
        self.compression_type = compression_type
        self.compression_level = compression_level
        self.min_size = min_size

    def serialize(self, value: Any) -> bytes:
        """Serialize and compress value."""
        try:
            # First serialize
            data = self.serializer.serialize(value)

            # Compress if above minimum size
            if len(data) >= self.min_size:
                compressed_data = self._compress(data)
                # Add compression header
                return b"COMPRESSED:" + compressed_data
            else:
                return data

        except Exception as e:
            logger.error(f"Compressed serialization failed: {e}")
            raise

    def deserialize(self, data: bytes) -> Any:
        """Decompress and deserialize value."""
        try:
            # Check if compressed
            if data.startswith(b"COMPRESSED:"):
                compressed_data = data[11:]  # Remove 'COMPRESSED:' prefix
                data = self._decompress(compressed_data)

            return self.serializer.deserialize(data)

        except Exception as e:
            logger.error(f"Compressed deserialization failed: {e}")
            raise

    def _compress(self, data: bytes) -> bytes:
        """Compress data using specified compression type."""
        if self.compression_type == CompressionType.GZIP:
            import gzip

            return gzip.compress(data, compresslevel=self.compression_level)
        elif self.compression_type == CompressionType.LZ4:
            try:
                import lz4.frame

                return lz4.frame.compress(
                    data, compression_level=self.compression_level
                )
            except ImportError:
                logger.warning("lz4 not available, falling back to gzip")
                import gzip

                return gzip.compress(data, compresslevel=self.compression_level)
        elif self.compression_type == CompressionType.ZSTD:
            try:
                import zstandard as zstd

                cctx = zstd.ZstdCompressor(level=self.compression_level)
                return cctx.compress(data)
            except ImportError:
                logger.warning("zstandard not available, falling back to gzip")
                import gzip

                return gzip.compress(data, compresslevel=self.compression_level)
        else:
            return data

    def _decompress(self, data: bytes) -> bytes:
        """Decompress data using specified compression type."""
        if self.compression_type == CompressionType.GZIP:
            import gzip

            return gzip.decompress(data)
        elif self.compression_type == CompressionType.LZ4:
            try:
                import lz4.frame

                return lz4.frame.decompress(data)
            except ImportError:
                logger.warning("lz4 not available, falling back to gzip")
                import gzip

                return gzip.decompress(data)
        elif self.compression_type == CompressionType.ZSTD:
            try:
                import zstandard as zstd

                dctx = zstd.ZstdDecompressor()
                return dctx.decompress(data)
            except ImportError:
                logger.warning("zstandard not available, falling back to gzip")
                import gzip

                return gzip.decompress(data)
        else:
            return data

    def get_size(self, value: Any) -> int:
        """Get compressed serialized size."""
        try:
            return len(self.serialize(value))
        except Exception:
            return 0


class CustomSerializer(CacheSerializer):
    """Custom cache serializer."""

    def __init__(
        self,
        serialize_func: callable,
        deserialize_func: callable,
        get_size_func: Optional[callable] = None,
    ):
        self.serialize_func = serialize_func
        self.deserialize_func = deserialize_func
        self.get_size_func = get_size_func or (lambda v: len(self.serialize(v)))

    def serialize(self, value: Any) -> bytes:
        """Serialize value using custom function."""
        try:
            return self.serialize_func(value)
        except Exception as e:
            logger.error(f"Custom serialization failed: {e}")
            raise

    def deserialize(self, data: bytes) -> Any:
        """Deserialize value using custom function."""
        try:
            return self.deserialize_func(data)
        except Exception as e:
            logger.error(f"Custom deserialization failed: {e}")
            raise

    def get_size(self, value: Any) -> int:
        """Get custom serialized size."""
        try:
            return self.get_size_func(value)
        except Exception:
            return 0


class SerializerFactory:
    """Factory for creating cache serializers."""

    @staticmethod
    def create_serializer(
        serialization_type: SerializationType,
        compression_type: CompressionType = CompressionType.NONE,
        compression_level: int = 6,
        compression_min_size: int = 1024,
        **kwargs,
    ) -> CacheSerializer:
        """Create cache serializer based on type and options."""

        # Create base serializer
        if serialization_type == SerializationType.JSON:
            serializer = JSONSerializer(**kwargs)
        elif serialization_type == SerializationType.ORJSON:
            serializer = ORJSONSerializer(**kwargs)
        elif serialization_type == SerializationType.PICKLE:
            serializer = PickleSerializer(**kwargs)
        elif serialization_type == SerializationType.MSGPACK:
            serializer = MessagePackSerializer(**kwargs)
        else:
            raise ValueError(f"Unsupported serialization type: {serialization_type}")

        # Add compression if requested
        if compression_type != CompressionType.NONE:
            serializer = CompressedSerializer(
                serializer,
                compression_type=compression_type,
                compression_level=compression_level,
                min_size=compression_min_size,
            )

        return serializer

    @staticmethod
    def create_custom_serializer(
        serialize_func: callable,
        deserialize_func: callable,
        get_size_func: Optional[callable] = None,
        compression_type: CompressionType = CompressionType.NONE,
        compression_level: int = 6,
        compression_min_size: int = 1024,
    ) -> CacheSerializer:
        """Create custom cache serializer."""
        serializer = CustomSerializer(serialize_func, deserialize_func, get_size_func)

        # Add compression if requested
        if compression_type != CompressionType.NONE:
            serializer = CompressedSerializer(
                serializer,
                compression_type=compression_type,
                compression_level=compression_level,
                min_size=compression_min_size,
            )

        return serializer


# Convenience functions
def get_json_serializer(compression: bool = False) -> CacheSerializer:
    """Get JSON serializer with optional compression."""
    compression_type = CompressionType.GZIP if compression else CompressionType.NONE
    return SerializerFactory.create_serializer(
        SerializationType.JSON, compression_type=compression_type
    )


def get_pickle_serializer(compression: bool = False) -> CacheSerializer:
    """Get Pickle serializer with optional compression."""
    compression_type = CompressionType.GZIP if compression else CompressionType.NONE
    return SerializerFactory.create_serializer(
        SerializationType.PICKLE, compression_type=compression_type
    )


def get_msgpack_serializer(compression: bool = False) -> CacheSerializer:
    """Get MessagePack serializer with optional compression."""
    compression_type = CompressionType.GZIP if compression else CompressionType.NONE
    return SerializerFactory.create_serializer(
        SerializationType.MSGPACK, compression_type=compression_type
    )


def get_orjson_serializer(compression: bool = False) -> CacheSerializer:
    """Get ORJSON serializer with optional compression."""
    compression_type = CompressionType.GZIP if compression else CompressionType.NONE
    return SerializerFactory.create_serializer(
        SerializationType.ORJSON, compression_type=compression_type
    )
