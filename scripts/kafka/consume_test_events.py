import json
import os

from kafka import KafkaConsumer

bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
topic = os.getenv("KAFKA_TEST_TOPIC", "api-test-events")
group_id = os.getenv("KAFKA_CONSUMER_GROUP", "demo-test-consumer")

consumer = KafkaConsumer(
    topic,
    bootstrap_servers=bootstrap_servers,
    auto_offset_reset="earliest",
    enable_auto_commit=True,
    group_id=group_id,
    value_deserializer=lambda value: json.loads(value.decode("utf-8")),
)

print(f"Listening topic={topic} bootstrap_servers={bootstrap_servers} group_id={group_id}")

for message in consumer:
    print(message.value)
