import json
import os
from pathlib import Path

from kafka import KafkaConsumer

BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = os.getenv("KAFKA_RAW_ORDERS_TOPIC", "raw-orders")
GROUP_ID = "audit-warehouse-group"
AUDIT_FILE = Path("scripts/demo_kafka/audit_raw_orders.txt")

consumer = KafkaConsumer(
    TOPIC,
    bootstrap_servers=BOOTSTRAP_SERVERS,
    group_id=GROUP_ID,
    auto_offset_reset="latest",
    enable_auto_commit=True,
    value_deserializer=lambda value: json.loads(value.decode("utf-8")),
)

print(f"[Audit] Listening topic={TOPIC} group_id={GROUP_ID}")
print(f"[Audit] Writing raw events to {AUDIT_FILE}")

for message in consumer:
    event = message.value
    with AUDIT_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(event, ensure_ascii=True) + "\n")

    print(f"[Audit] Stored event_id={event.get('event_id')} into audit log")
