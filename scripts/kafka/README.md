# Kafka Local Setup (Docker)

## Start Kafka + Kafka UI

```bash
docker compose -f docker-compose.kafka.yml up -d
```

## Check containers

```bash
docker compose -f docker-compose.kafka.yml ps
```

## Stop

```bash
docker compose -f docker-compose.kafka.yml down
```

## Stop and remove data volume

```bash
docker compose -f docker-compose.kafka.yml down -v
```

## Endpoints

- Kafka broker: localhost:9092
- Kafka UI: http://localhost:8081

## App environment

Set these values in `.env`:

```env
ENABLE_KAFKA=True
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TEST_TOPIC=api-test-events
```

## Quick test flow

1. Start backend API.
2. Run consumer:

```bash
python scripts/kafka/consume_test_events.py
```

3. Call API:

```bash
curl http://127.0.0.1:8000/api/test
```

You should see one event in consumer output for each request.
