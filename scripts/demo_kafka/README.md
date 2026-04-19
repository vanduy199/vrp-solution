# Kafka Fan-out Demo (raw-orders)

Muc tieu:
- 1 request tao don hang -> event vao topic raw-orders
- 3 microservice voi 3 group_id khac nhau deu nhan cung mot event

## 1) Start Kafka

```bash
sudo docker compose -f docker-compose.kafka.yml up -d
```

Hoac dung script all-in-one:

```bash
bash scripts/demo_kafka/run_fanout_demo.sh start
```

## 2) Start API

```bash
uvicorn main:app --reload
```

## 3) Mo 3 terminal consumers

```bash
python scripts/demo_kafka/consumer_vrp_solver.py
python scripts/demo_kafka/consumer_notification.py
python scripts/demo_kafka/consumer_audit.py
```

## 4) Ban fake order event

```bash
curl -X POST http://127.0.0.1:8000/api/demo/kafka/orders \
  -H "Content-Type: application/json" \
  -d '{"customer_name":"Tran Thi B","phone":"0909123123","address":"45 Hai Ba Trung"}'
```

Hoac:

```bash
bash scripts/demo_kafka/run_fanout_demo.sh send "Tran Thi B" "0909123123" "45 Hai Ba Trung"
```

## 5) Ky vong

- VRP Solver: nhan event va sleep 5s
- Notification: in thong bao gui SMS ngay
- Audit: ghi event vao scripts/demo_kafka/audit_raw_orders.txt
- Ca 3 deu nhan cung 1 event vi 3 group_id khac nhau

## Script dieu khien nhanh

```bash
bash scripts/demo_kafka/run_fanout_demo.sh status
bash scripts/demo_kafka/run_fanout_demo.sh logs 50
bash scripts/demo_kafka/run_fanout_demo.sh stop
```
