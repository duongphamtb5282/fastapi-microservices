"""
Kafka message producer implementation.
"""

import json
from typing import Any, Dict, List, Optional

from kafka import KafkaProducer
from kafka.errors import KafkaError

from ncm_foundation.core.config import get_settings
from ncm_foundation.core.logging import logger
from ncm_foundation.core.messaging.interfaces import MessageProducer


class KafkaMessageProducer(MessageProducer):
    """Kafka message producer implementation."""

    def __init__(self, settings=None):
        self._settings = settings or get_settings()
        self._producer: Optional[KafkaProducer] = None
        logger.info("KafkaMessageProducer initialized")

    async def connect(self) -> None:
        """Establish connection to Kafka."""
        if not self._producer:
            self._producer = KafkaProducer(
                bootstrap_servers=self._settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
            )
            logger.info("Connected to Kafka producer")

    async def send_message(
        self,
        topic: str,
        message: Any,
        key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        """Send a message to a Kafka topic."""
        if not self._producer:
            await self.connect()

        try:
            future = self._producer.send(topic, message, key=key, headers=headers)
            future.get(timeout=10)  # Wait for the message to be sent
            logger.debug("Message sent to Kafka", topic=topic, key=key)
        except KafkaError as e:
            logger.error("Failed to send message to Kafka", topic=topic, error=str(e))
            raise

    async def send_batch(
        self,
        topic: str,
        messages: List[Any],
        key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        """Send multiple messages to a Kafka topic."""
        if not self._producer:
            await self.connect()

        try:
            futures = []
            for message in messages:
                future = self._producer.send(topic, message, key=key, headers=headers)
                futures.append(future)

            # Wait for all messages to be sent
            for future in futures:
                future.get(timeout=10)
            logger.debug(
                "Batch messages sent to Kafka", topic=topic, count=len(messages)
            )
        except KafkaError as e:
            logger.error(
                "Failed to send batch messages to Kafka", topic=topic, error=str(e)
            )
            raise

    async def close(self) -> None:
        """Close the Kafka producer connection."""
        if self._producer:
            self._producer.close()
            self._producer = None
            logger.info("Kafka producer connection closed")
