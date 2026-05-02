import json
import logging
from typing import Any

try:
    from kafka import KafkaProducer
    from kafka.errors import KafkaError as KafkaLibError
except ImportError:
    KafkaProducer = None  # type: ignore[assignment]
    KafkaLibError = Exception

from app.core.config import settings

logger = logging.getLogger(__name__)

_producer: Any | None = None


def _build_producer() -> Any:
    if KafkaProducer is None:
        raise RuntimeError("kafka-python is not installed")
    return KafkaProducer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        retries=1,
        request_timeout_ms=3000,
        api_version_auto_timeout_ms=3000,
    )


def _get_producer() -> Any | None:
    global _producer
    if not settings.ENABLE_KAFKA:
        return None
    if _producer is None:
        try:
            _producer = _build_producer()
        except Exception as exc:
            logger.warning("Kafka producer init failed: %s", exc)
            return None
    return _producer


def publish(topic: str, payload: dict[str, Any]) -> None:
    producer = _get_producer()
    if producer is None:
        logger.info("Kafka disabled. Skip publish to %s", topic)
        return
    try:
        producer.send(topic, value=payload)
    except KafkaLibError as exc:
        logger.warning("Kafka publish failed (topic=%s): %s", topic, exc)


def publish_test_event(payload: dict[str, Any]) -> None:
    publish(settings.KAFKA_TEST_TOPIC, payload)
