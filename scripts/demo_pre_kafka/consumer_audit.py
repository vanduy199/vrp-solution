import json
import time
from pathlib import Path

import httpx

API_BASE = "http://127.0.0.1:8000/api/demo"
CONSUMER_NAME = "audit-warehouse"
AUDIT_FILE = Path("scripts/demo_pre_kafka/audit_log.txt")

print("[Audit] Listening for legacy queue messages...")
print(f"[Audit] Writing consumed raw events to: {AUDIT_FILE}")

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
            with AUDIT_FILE.open("a", encoding="utf-8") as file:
                file.write(json.dumps(event, ensure_ascii=True) + "\n")
            print(f"[Audit] Stored raw event {event['event_id']} to audit log.")
        else:
            time.sleep(1)
    except Exception as exc:
        print(f"[Audit] Error: {exc}")
        time.sleep(2)
