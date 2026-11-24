import asyncio
import os
import time
import uuid

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from shop.common.telemetry import CACHE_HIT_RATE, DB_POOL_IN_USE, setup_telemetry

app = FastAPI(title="Shop: Orders Service")
logger = setup_telemetry(app, "orders")

# Simulated state & chaos injection settings
MAX_DB_POOL_SIZE = int(os.getenv("MAX_DB_POOL_SIZE", "10"))
ACTIVE_DB_CONNECTIONS = 0
FORCE_DB_POOL_EXHAUSTION = False
SIMULATE_SLOW_QUERY = False
ORDERS_CACHE = {}  # In-memory Redis simulation fallback
ORDERS_DB = {}  # In-memory Postgres simulation fallback


class OrderItem(BaseModel):
    item_id: str
    quantity: int
    unit_price: float


class CreateOrderRequest(BaseModel):
    items: list[OrderItem]
    total_amount: float
    customer_id: str


class OrderResponse(BaseModel):
    order_id: str
    status: str
    total_amount: float
    items: list[OrderItem]
    created_at: float


@app.get("/health")
def health():
    return {"status": "ok", "service": "orders"}


@app.post("/chaos/pool_exhaust")
def toggle_pool_exhaust(enabled: bool = True):
    global FORCE_DB_POOL_EXHAUSTION, ACTIVE_DB_CONNECTIONS
    FORCE_DB_POOL_EXHAUSTION = enabled
    ACTIVE_DB_CONNECTIONS = MAX_DB_POOL_SIZE if enabled else 2
    DB_POOL_IN_USE.labels(service="orders").set(ACTIVE_DB_CONNECTIONS)
    logger.warning(
        "chaos_db_pool_updated",
        forced_exhaustion=enabled,
        connections=ACTIVE_DB_CONNECTIONS,
    )
    return {
        "forced_exhaustion": FORCE_DB_POOL_EXHAUSTION,
        "active_connections": ACTIVE_DB_CONNECTIONS,
    }


@app.post("/chaos/slow_query")
def toggle_slow_query(enabled: bool = True):
    global SIMULATE_SLOW_QUERY
    SIMULATE_SLOW_QUERY = enabled
    logger.warning("chaos_slow_query_updated", enabled=enabled)
    return {"simulate_slow_query": SIMULATE_SLOW_QUERY}


@app.post("/orders", response_model=OrderResponse)
async def create_order(req: CreateOrderRequest):
    global ACTIVE_DB_CONNECTIONS

    # Check connection pool exhaustion fault
    if FORCE_DB_POOL_EXHAUSTION or ACTIVE_DB_CONNECTIONS >= MAX_DB_POOL_SIZE:
        DB_POOL_IN_USE.labels(service="orders").set(MAX_DB_POOL_SIZE)
        logger.error(
            "db_pool_exhaustion_error",
            msg="FATAL: remaining connection slots are reserved for non-replication superuser connections. Pool limit reached.",
            active_connections=MAX_DB_POOL_SIZE,
            max_connections=MAX_DB_POOL_SIZE,
        )
        raise HTTPException(
            status_code=500,
            detail="Database connection pool exhausted: too many connections",
        )

    # Acquire connection
    ACTIVE_DB_CONNECTIONS += 1
    DB_POOL_IN_USE.labels(service="orders").set(ACTIVE_DB_CONNECTIONS)

    try:
        # Simulate slow query if enabled
        if SIMULATE_SLOW_QUERY:
            logger.warning(
                "slow_query_execution",
                query="SELECT * FROM orders WHERE ...",
                duration_ms=4200,
            )
            await asyncio.sleep(3.5)

        order_id = f"ord_{uuid.uuid4().hex[:8]}"
        order = {
            "order_id": order_id,
            "status": "pending_payment",
            "total_amount": req.total_amount,
            "items": [item.dict() for item in req.items],
            "created_at": time.time(),
        }
        ORDERS_DB[order_id] = order
        ORDERS_CACHE[order_id] = order  # update cache
        CACHE_HIT_RATE.labels(service="orders").set(0.92)

        logger.info(
            "order_created_successfully", order_id=order_id, amount=req.total_amount
        )
        return order
    finally:
        ACTIVE_DB_CONNECTIONS = max(0, ACTIVE_DB_CONNECTIONS - 1)
        DB_POOL_IN_USE.labels(service="orders").set(ACTIVE_DB_CONNECTIONS)


@app.get("/orders/{order_id}")
async def get_order(order_id: str):
    if order_id in ORDERS_CACHE:
        CACHE_HIT_RATE.labels(service="orders").set(0.95)
        logger.info("cache_hit", order_id=order_id)
        return ORDERS_CACHE[order_id]

    if order_id in ORDERS_DB:
        CACHE_HIT_RATE.labels(service="orders").set(0.30)
        logger.info("cache_miss_db_fallback", order_id=order_id)
        return ORDERS_DB[order_id]

    logger.warning("order_not_found", order_id=order_id)
    raise HTTPException(status_code=404, detail="Order not found")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
