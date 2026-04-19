import json
import os
import time

from kafka import KafkaConsumer

BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = os.getenv("KAFKA_RAW_ORDERS_TOPIC", "raw-orders")
GROUP_ID = "vrp-solver-group"

consumer = KafkaConsumer(
    TOPIC,
    bootstrap_servers=BOOTSTRAP_SERVERS,
    group_id=GROUP_ID,
    auto_offset_reset="latest",
    enable_auto_commit=True,
    value_deserializer=lambda value: json.loads(value.decode("utf-8")),
)

print(f"[VRP Solver] Listening topic={TOPIC} group_id={GROUP_ID}")

for message in consumer:
    event = message.value
    order = event.get("order", {})
    customer_name = order.get("customer_name", "unknown")

    print(f"[VRP Solver] Received event_id={event.get('event_id')} customer={customer_name}. Optimizing route (5s)...")
    time.sleep(5)
    print(f"[VRP Solver] Done event_id={event.get('event_id')}")
