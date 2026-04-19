import json
import os

from kafka import KafkaConsumer

BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = os.getenv("KAFKA_RAW_ORDERS_TOPIC", "raw-orders")
GROUP_ID = "notification-service-group"

consumer = KafkaConsumer(
    TOPIC,
    bootstrap_servers=BOOTSTRAP_SERVERS,
    group_id=GROUP_ID,
    auto_offset_reset="latest",
    enable_auto_commit=True,
    value_deserializer=lambda value: json.loads(value.decode("utf-8")),
)

print(f"[Notification] Listening topic={TOPIC} group_id={GROUP_ID}")

for message in consumer:
    event = message.value
    order = event.get("order", {})
    print(
        "[Notification] Da gui SMS cho khach hang "
        f"{order.get('customer_name', 'unknown')} ({order.get('phone', 'unknown')}): "
        "Don dang duoc dieu phoi"
    )
