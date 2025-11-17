"""
Kafka message broker implementation.
"""

from typing import List, Optional

from kafka.admin import ConfigResource, ConfigResourceType, KafkaAdminClient
from kafka.errors import KafkaError

from ncm_foundation.core.config import get_settings
from ncm_foundation.core.logging import logger
from ncm_foundation.core.messaging.interfaces import (
    MessageBroker,
    MessageConsumer,
    MessageProducer,
)
from ncm_foundation.core.messaging.kafka_consumer import KafkaMessageConsumer
from ncm_foundation.core.messaging.kafka_producer import KafkaMessageProducer


class KafkaMessageBroker(MessageBroker):
    """Kafka message broker implementation."""

    def __init__(self, settings=None):
        self._settings = settings or get_settings()
        self._admin_client: Optional[KafkaAdminClient] = None
        logger.info("KafkaMessageBroker initialized")

    async def connect(self) -> None:
        """Establish connection to Kafka admin client."""
        if not self._admin_client:
            self._admin_client = KafkaAdminClient(
                bootstrap_servers=self._settings.KAFKA_BOOTSTRAP_SERVERS,
                client_id="ncm-foundation-admin",
            )
            logger.info("Connected to Kafka admin client")

    async def create_producer(self) -> MessageProducer:
        """Create a Kafka message producer."""
        producer = KafkaMessageProducer(self._settings)
        await producer.connect()
        return producer

    async def create_consumer(self, group_id: str) -> MessageConsumer:
        """Create a Kafka message consumer."""
        consumer = KafkaMessageConsumer(self._settings, group_id)
        return consumer

    async def create_topic(
        self, topic: str, partitions: int = 1, replication_factor: int = 1
    ) -> None:
        """Create a Kafka topic."""
        if not self._admin_client:
            await self.connect()

        try:
            from kafka.admin import NewTopic

            topic_list = [
                NewTopic(
                    name=topic,
                    num_partitions=partitions,
                    replication_factor=replication_factor,
                )
            ]
            fs = self._admin_client.create_topics(topic_list)

            for topic_name, f in fs.items():
                try:
                    f.result()  # The result itself is None
                    logger.info(
                        "Topic created successfully",
                        topic=topic_name,
                        partitions=partitions,
                        replication_factor=replication_factor,
                    )
                except Exception as e:
                    if "Topic already exists" in str(e):
                        logger.info("Topic already exists", topic=topic_name)
                    else:
                        logger.error(
                            "Failed to create topic", topic=topic_name, error=str(e)
                        )
                        raise
        except KafkaError as e:
            logger.error("Failed to create topic", topic=topic, error=str(e))
            raise

    async def delete_topic(self, topic: str) -> None:
        """Delete a Kafka topic."""
        if not self._admin_client:
            await self.connect()

        try:
            fs = self._admin_client.delete_topics([topic])
            for topic_name, f in fs.items():
                try:
                    f.result()  # The result itself is None
                    logger.info("Topic deleted successfully", topic=topic_name)
                except Exception as e:
                    logger.error(
                        "Failed to delete topic", topic=topic_name, error=str(e)
                    )
                    raise
        except KafkaError as e:
            logger.error("Failed to delete topic", topic=topic, error=str(e))
            raise

    async def list_topics(self) -> List[str]:
        """List all Kafka topics."""
        if not self._admin_client:
            await self.connect()

        try:
            metadata = self._admin_client.describe_cluster()
            topics = list(metadata.topics.keys())
            logger.debug("Listed topics", count=len(topics))
            return topics
        except KafkaError as e:
            logger.error("Failed to list topics", error=str(e))
            raise

    async def close(self) -> None:
        """Close the Kafka admin client connection."""
        if self._admin_client:
            self._admin_client.close()
            self._admin_client = None
            logger.info("Kafka admin client connection closed")
