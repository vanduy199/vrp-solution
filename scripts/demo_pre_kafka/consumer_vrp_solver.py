import time

import httpx

API_BASE = "http://127.0.0.1:8000/api/demo"
CONSUMER_NAME = "vrp-solver"

print("[VRP Solver] Listening for legacy queue messages...")

while True:
    try:
        response = httpx.post(
            f"{API_BASE}/legacy/consume",
            params={"consumer_name": CONSUMER_NAME},
            timeout=10,
        )
        payload = response.json()
        message_data = payload.get("data")

        if message_data and message_data.get("event"):
            event = message_data["event"]
            customer_name = event["order"]["customer_name"]
            print(f"[VRP Solver] Picked event {event['event_id']} for {customer_name}. Simulating route optimization (5s)...")
            time.sleep(5)
            print(f"[VRP Solver] Done optimizing route for event {event['event_id']}.")
        else:
            time.sleep(1)
    except Exception as exc:
        print(f"[VRP Solver] Error: {exc}")
        time.sleep(2)
