import time

import httpx

API_BASE = "http://127.0.0.1:8000/api/demo"
CONSUMER_NAME = "notification-service"

print("[Notification] Listening for legacy queue messages...")

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
            order = event["order"]
            print(
                "[Notification] Da gui SMS cho khach hang "
                f"{order['customer_name']} ({order['phone']}): Don dang duoc dieu phoi."
            )
        else:
            time.sleep(1)
    except Exception as exc:
        print(f"[Notification] Error: {exc}")
        time.sleep(2)
