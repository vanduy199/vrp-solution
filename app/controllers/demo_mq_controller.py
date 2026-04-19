from collections import deque
from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel, Field

from app.services.kafka_service import publish_raw_order_event

router = APIRouter(prefix="/demo")

# Shared in-memory queue to simulate traditional MQ semantics.
# Once a message is consumed, it is removed and no other service can read it.
_legacy_queue: deque[dict] = deque()
_legacy_queue_lock = Lock()


class CreateOrderRequest(BaseModel):
    customer_name: str = Field(..., min_length=1)
    phone: str = Field(..., min_length=1)
    address: str = Field(..., min_length=1)


@router.post("/legacy/orders")
def create_order(payload: CreateOrderRequest):
    order_event = {
        "event_id": str(uuid4()),
        "event_type": "ORDER_CREATED",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "order": payload.model_dump(),
    }


@router.post("/kafka/orders")
def create_order_kafka(payload: CreateOrderRequest, background_tasks: BackgroundTasks):
    order_event = {
        "event_id": str(uuid4()),
        "event_type": "ORDER_CREATED",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "order": payload.model_dump(),
        "source": "demo-kafka",
    }

    background_tasks.add_task(publish_raw_order_event, order_event)

    return {
        "success": True,
        "message": "Order accepted and queued for Kafka topic raw-orders.",
        "data": {
            "event_id": order_event["event_id"],
            "topic": "raw-orders",
        },
    }

    with _legacy_queue_lock:
        _legacy_queue.append(order_event)
        queue_size = len(_legacy_queue)

    return {
        "success": True,
        "message": "Order event has been queued in legacy MQ mode.",
        "data": {
            "event_id": order_event["event_id"],
            "queue_size": queue_size,
        },
    }


@router.post("/legacy/consume")
def consume_one_message(consumer_name: str):
    with _legacy_queue_lock:
        if not _legacy_queue:
            return {
                "success": True,
                "message": "No message available.",
                "data": None,
            }

        event = _legacy_queue.popleft()
        queue_size = len(_legacy_queue)

    return {
        "success": True,
        "message": "Message consumed and removed from queue.",
        "data": {
            "consumer": consumer_name,
            "remaining_queue_size": queue_size,
            "event": event,
        },
    }


@router.get("/legacy/queue-size")
def queue_size():
    with _legacy_queue_lock:
        size = len(_legacy_queue)

    return {
        "success": True,
        "data": {
            "queue_size": size,
        },
    }
