"""
Messaging Services for NCM Sample Project.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List

from ncm_foundation import get_logger
from ncm_foundation.core.messaging.circuit_breaker import CircuitBreaker
from ncm_foundation.core.messaging.kafka_consumer import KafkaMessageConsumer
from ncm_foundation.core.messaging.kafka_producer import KafkaMessageProducer
from ncm_sample.config import settings

logger = get_logger(__name__)


class MessagingRepository:
    """Repository for messaging operations."""

    def __init__(self, producer: KafkaMessageProducer):
        self.producer = producer

    async def publish_event(
        self,
        topic: str,
        message: Dict[str, Any],
        key: str = None,
        headers: Dict[str, str] = None,
    ):
        """Publish event to Kafka topic."""
        await self.producer.send_message(topic, message, key=key, headers=headers)


class MessagingService:
    """Messaging service with Kafka integration and circuit breaker."""

    def __init__(self):
        self.producer = KafkaMessageProducer()
        self.consumer = None
        self.messaging_repository = MessagingRepository(self.producer)
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=settings.get("circuit_breaker_failure_threshold", 5),
            recovery_timeout=settings.get("circuit_breaker_recovery_timeout", 60),
        )
        self.message_handlers = {}

    async def start(self):
        """Start messaging service."""
        await self.producer.connect()
        logger.info("Messaging service started")

    async def stop(self):
        """Stop messaging service."""
        if self.producer:
            await self.producer.disconnect()
        if self.consumer:
            await self.consumer.stop()
        logger.info("Messaging service stopped")

    async def publish_user_event(
        self, event_type: str, user_data: Dict[str, Any], user_id: str = None
    ):
        """Publish user-related events to Kafka using repository."""
        try:
            message = {
                "event_type": event_type,
                "timestamp": datetime.utcnow().isoformat(),
                "user_id": user_id,
                "data": user_data,
                "service": "ncm-sample",
            }

            topic = f"{settings.kafka_topic_prefix}.user.{event_type}"

            async def send_message():
                await self.messaging_repository.publish_event(
                    topic=topic,
                    message=message,
                    key=user_id or "system",
                    headers={"event_type": event_type},
                )

            # Use circuit breaker for message sending
            await self.circuit_breaker.call(send_message)

            logger.info(f"Published {event_type} event for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to publish user event: {e}")

    async def publish_system_event(self, event_type: str, data: Dict[str, Any]):
        """Publish system events to Kafka using repository."""
        try:
            message = {
                "event_type": event_type,
                "timestamp": datetime.utcnow().isoformat(),
                "data": data,
                "service": "ncm-sample",
            }

            topic = f"{settings.kafka_topic_prefix}.system.{event_type}"

            async def send_message():
                await self.messaging_repository.publish_event(
                    topic=topic,
                    message=message,
                    key="system",
                    headers={"event_type": event_type},
                )

            # Use circuit breaker for message sending
            await self.circuit_breaker.call(send_message)

            logger.info(f"Published {event_type} system event")

        except Exception as e:
            logger.error(f"Failed to publish system event: {e}")

    def register_message_handler(self, event_type: str, handler_func):
        """Register a message handler for specific event types."""
        self.message_handlers[event_type] = handler_func
        logger.info(f"Registered handler for event type: {event_type}")

    async def start_consuming(
        self, topics: List[str], group_id: str = "ncm-sample-consumer"
    ):
        """Start consuming messages from Kafka topics."""
        self.consumer = KafkaMessageConsumer(
            topics=topics, group_id=group_id, auto_commit=True
        )

        await self.consumer.start()

        # Start message processing loop
        asyncio.create_task(self._consume_messages())

        logger.info(f"Started consuming from topics: {topics}")

    async def _consume_messages(self):
        """Internal method to consume and process messages."""
        if not self.consumer:
            return

        try:
            async for message in self.consumer:
                try:
                    event_type = message.get("event_type")
                    if event_type and event_type in self.message_handlers:
                        # Process message with handler
                        await self.message_handlers[event_type](message)
                        logger.debug(f"Processed message of type: {event_type}")
                    else:
                        logger.warning(f"No handler for event type: {event_type}")

                except Exception as e:
                    logger.error(f"Error processing message: {e}")

        except Exception as e:
            logger.error(f"Error in message consumption loop: {e}")


class NotificationService:
    """Service for handling notifications via messaging."""

    def __init__(self, messaging_service: MessagingService):
        self.messaging = messaging_service

    async def notify_user_created(self, user: User):
        """Notify about user creation."""
        await self.messaging.publish_user_event(
            "user_created",
            {
                "user_id": str(user.id),
                "email": user.email,
                "username": user.username,
                "created_at": user.created_at.isoformat(),
                "created_by": user.created_by,
            },
            str(user.id),
        )

    async def notify_user_updated(self, user: User, changes: Dict[str, Any]):
        """Notify about user updates."""
        await self.messaging.publish_user_event(
            "user_updated",
            {
                "user_id": str(user.id),
                "changes": changes,
                "updated_at": user.updated_at.isoformat(),
                "updated_by": user.updated_by,
            },
            str(user.id),
        )

    async def notify_user_deleted(self, user_id: str, deleted_by: str):
        """Notify about user deletion."""
        await self.messaging.publish_user_event(
            "user_deleted",
            {
                "user_id": user_id,
                "deleted_at": datetime.utcnow().isoformat(),
                "deleted_by": deleted_by,
            },
            user_id,
        )
