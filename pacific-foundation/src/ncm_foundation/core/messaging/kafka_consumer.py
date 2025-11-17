"""
Kafka message consumer implementation.
"""

import asyncio
import json
from typing import Any, Awaitable, Callable, Dict, List, Optional

from kafka import KafkaConsumer
from kafka.errors import KafkaError

from ncm_foundation.core.config import get_settings
from ncm_foundation.core.logging import logger
from ncm_foundation.core.messaging.interfaces import MessageConsumer


class KafkaMessageConsumer(MessageConsumer):
    """Kafka message consumer implementation."""

    def __init__(self, settings=None, group_id: str = "default"):
        self._settings = settings or get_settings()
        self._group_id = group_id
        self._consumer: Optional[KafkaConsumer] = None
        self._topics: List[str] = []
        self._handler: Optional[Callable[[Any], Awaitable[None]]] = None
        self._consuming = False
        logger.info("KafkaMessageConsumer initialized", group_id=group_id)

    async def connect(self) -> None:
        """Establish connection to Kafka."""
        if not self._consumer:
            self._consumer = KafkaConsumer(
                *self._topics,
                bootstrap_servers=self._settings.KAFKA_BOOTSTRAP_SERVERS,
                group_id=self._group_id,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                key_deserializer=lambda k: k.decode("utf-8") if k else None,
                auto_offset_reset="earliest",
                enable_auto_commit=True,
            )
            logger.info("Connected to Kafka consumer", topics=self._topics)

    async def subscribe(
        self, topics: List[str], handler: Callable[[Any], Awaitable[None]]
    ) -> None:
        """Subscribe to topics and set up message handler."""
        self._topics = topics
        self._handler = handler
        logger.info("Subscribed to topics", topics=topics)

    async def start_consuming(self) -> None:
        """Start consuming messages."""
        if not self._consumer:
            await self.connect()

        if not self._handler:
            raise ValueError("No message handler set. Call subscribe() first.")

        self._consuming = True
        logger.info("Started consuming messages")

        try:
            for message in self._consumer:
                if not self._consuming:
                    break

                try:
                    await self._handler(message.value)
                    logger.debug(
                        "Message processed successfully",
                        topic=message.topic,
                        partition=message.partition,
                        offset=message.offset,
                    )
                except Exception as e:
                    logger.error(
                        "Error processing message", topic=message.topic, error=str(e)
                    )
                    # In a production system, you might want to implement dead letter queue here
        except KafkaError as e:
            logger.error("Kafka consumer error", error=str(e))
            raise
        finally:
            self._consuming = False

    async def stop_consuming(self) -> None:
        """Stop consuming messages."""
        self._consuming = False
        logger.info("Stopped consuming messages")

    async def close(self) -> None:
        """Close the Kafka consumer connection."""
        await self.stop_consuming()
        if self._consumer:
            self._consumer.close()
            self._consumer = None
            logger.info("Kafka consumer connection closed")
