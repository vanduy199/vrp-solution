import json
import logging
import os
from typing import Any

try:
    from kafka import KafkaProducer
    from kafka.errors import KafkaError as KafkaLibError
except ImportError:  # pragma: no cover
    KafkaProducer = None  # type: ignore[assignment]
    KafkaLibError = Exception

logger = logging.getLogger(__name__)

_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
_TEST_TOPIC = os.getenv("KAFKA_TEST_TOPIC", "api-test-events")
_RAW_ORDERS_TOPIC = os.getenv("KAFKA_RAW_ORDERS_TOPIC", "raw-orders")
_ENABLE_KAFKA = os.getenv("ENABLE_KAFKA", "true").lower() == "true"

_producer: Any | None = None


def _build_producer() -> Any:
    if KafkaProducer is None:
        raise RuntimeError("kafka-python is not installed")

    # Keep timeouts low so Kafka issues do not stall API thread for too long.
    return KafkaProducer(
        bootstrap_servers=_BOOTSTRAP_SERVERS,
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
        retries=1,
        request_timeout_ms=3000,
        api_version_auto_timeout_ms=3000,
    )


def _get_producer() -> Any | None:
    global _producer

    if not _ENABLE_KAFKA:
        return None

    if _producer is None:
        try:
            _producer = _build_producer()
            logger.info("Kafka producer initialized. bootstrap_servers=%s", _BOOTSTRAP_SERVERS)
        except Exception as exc:  # pragma: no cover
            logger.warning("Kafka producer initialization failed: %s", exc)
            return None

    return _producer


def publish_test_event(event_payload: dict[str, Any]) -> None:
    producer = _get_producer()
    if producer is None:
        logger.info("Kafka disabled or unavailable. Skip publishing event_id=%s", event_payload.get("event_id"))
        return

    try:
        producer.send(_TEST_TOPIC, value=event_payload)
    except KafkaLibError as exc:
        logger.warning("Failed to publish test event to Kafka: %s", exc)


def publish_raw_order_event(event_payload: dict[str, Any]) -> None:
    producer = _get_producer()
    if producer is None:
        logger.info("Kafka disabled or unavailable. Skip raw order event_id=%s", event_payload.get("event_id"))
        return

    try:
        producer.send(_RAW_ORDERS_TOPIC, value=event_payload)
    except KafkaLibError as exc:
        logger.warning("Failed to publish raw order event to Kafka: %s", exc)
