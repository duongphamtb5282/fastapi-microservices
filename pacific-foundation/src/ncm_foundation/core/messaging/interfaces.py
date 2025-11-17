"""
Abstract interfaces for messaging system.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional


class MessageBrokerType(Enum):
    """Enum for supported message broker types."""

    KAFKA = "kafka"
    RABBITMQ = "rabbitmq"
    REDIS = "redis"


class MessageProducer(ABC):
    """Abstract base class for message producers."""

    @abstractmethod
    async def send_message(
        self,
        topic: str,
        message: Any,
        key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        """Send a message to a topic."""
        pass

    @abstractmethod
    async def send_batch(
        self,
        topic: str,
        messages: List[Any],
        key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        """Send multiple messages to a topic."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the producer connection."""
        pass


class MessageConsumer(ABC):
    """Abstract base class for message consumers."""

    @abstractmethod
    async def subscribe(
        self, topics: List[str], handler: Callable[[Any], Awaitable[None]]
    ) -> None:
        """Subscribe to topics and set up message handler."""
        pass

    @abstractmethod
    async def start_consuming(self) -> None:
        """Start consuming messages."""
        pass

    @abstractmethod
    async def stop_consuming(self) -> None:
        """Stop consuming messages."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the consumer connection."""
        pass


class MessageBroker(ABC):
    """Abstract base class for message brokers."""

    @abstractmethod
    async def create_producer(self) -> MessageProducer:
        """Create a message producer."""
        pass

    @abstractmethod
    async def create_consumer(self, group_id: str) -> MessageConsumer:
        """Create a message consumer."""
        pass

    @abstractmethod
    async def create_topic(
        self, topic: str, partitions: int = 1, replication_factor: int = 1
    ) -> None:
        """Create a topic."""
        pass

    @abstractmethod
    async def delete_topic(self, topic: str) -> None:
        """Delete a topic."""
        pass

    @abstractmethod
    async def list_topics(self) -> List[str]:
        """List all topics."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the broker connection."""
        pass
