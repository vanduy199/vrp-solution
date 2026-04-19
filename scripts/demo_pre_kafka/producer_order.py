import argparse

import httpx

API_URL = "http://127.0.0.1:8000/api/demo/legacy/orders"


def main():
    parser = argparse.ArgumentParser(description="Create one demo order event in legacy MQ mode.")
    parser.add_argument("--customer", default="Nguyen Van A")
    parser.add_argument("--phone", default="0900000001")
    parser.add_argument("--address", default="123 Le Loi, Q1")
    args = parser.parse_args()

    payload = {
        "customer_name": args.customer,
        "phone": args.phone,
        "address": args.address,
    }

    response = httpx.post(API_URL, json=payload, timeout=10)
    response.raise_for_status()
    print(response.json())


if __name__ == "__main__":
    main()
