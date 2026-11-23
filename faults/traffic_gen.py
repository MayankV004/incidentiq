import asyncio
import os
import random
import sys

import httpx

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8001")
CONCURRENCY = int(os.getenv("CONCURRENCY", "2"))
ITEMS_CATALOG = [
    {"item_id": "item_phone", "unit_price": 599.99},
    {"item_id": "item_laptop", "unit_price": 1299.00},
    {"item_id": "item_cable", "unit_price": 19.99},
    {"item_id": "item_headphones", "unit_price": 149.50},
]


async def send_traffic():
    print(f"[*] Starting Traffic Generator -> {GATEWAY_URL}")
    async with httpx.AsyncClient(timeout=15.0) as client:
        while True:
            # Pick 1-3 random items
            selected_items = [
                {
                    "item_id": item["item_id"],
                    "quantity": random.randint(1, 2),
                    "unit_price": item["unit_price"],
                }
                for item in random.sample(ITEMS_CATALOG, random.randint(1, 3))
            ]

            payload = {
                "items": selected_items,
                "customer_id": f"cust_{random.randint(100, 999)}",
            }

            try:
                resp = await client.post(f"{GATEWAY_URL}/checkout", json=payload)
                status_color = "\033[92m" if resp.status_code == 200 else "\033[91m"
                reset_color = "\033[0m"
                print(
                    f"[Traffic] Status: {status_color}{resp.status_code}{reset_color} "
                    f"Payload size: {len(selected_items)} items"
                )
            except httpx.HTTPError as e:
                print(f"[Traffic Error] Gateway unreachable: {e}", file=sys.stderr)

            await asyncio.sleep(random.uniform(0.5, 1.5))


if __name__ == "__main__":
    try:
        asyncio.run(send_traffic())
    except KeyboardInterrupt:
        print("\nTraffic generator stopped.")
