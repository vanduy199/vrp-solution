# Demo Pre-Kafka (Traditional Queue)

Muc tieu demo:
- Gia lap he thong chua co Kafka, message bi consume 1 lan va bien mat.
- Chay 3 service consumer song song, nhung khi ban 1 order thi chi 1 service nhan duoc event.

## 1) Start API

Tai root backend (`vrp-solution/`):

```bash
uvicorn main:app --reload
```

## 2) Mo 3 terminal, chay 3 consumers

```bash
python scripts/demo_pre_kafka/consumer_vrp_solver.py
python scripts/demo_pre_kafka/consumer_notification.py
python scripts/demo_pre_kafka/consumer_audit.py
```

## 3) Ban 1 order event

```bash
python scripts/demo_pre_kafka/producer_order.py --customer "Tran Thi B" --phone "0909123123" --address "45 Hai Ba Trung"
```

## 4) Ky vong ket qua

- Chi 1 trong 3 terminal consumer in log da nhan event.
- 2 terminal con lai khong nhan duoc event do message da bi pop khoi queue.
- Day la han che cua queue truyen thong khi can fan-out cho nhieu he thong.

## 5) Kiem tra queue size

```bash
curl -s http://127.0.0.1:8000/api/demo/legacy/queue-size
```
