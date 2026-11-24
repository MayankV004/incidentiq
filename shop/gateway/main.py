import os

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from shop.common.telemetry import setup_telemetry

app = FastAPI(title="Shop: API Gateway")
logger = setup_telemetry(app, "gateway")

ORDERS_SERVICE_URL = os.getenv("ORDERS_SERVICE_URL", "http://localhost:8002")
PAYMENTS_SERVICE_URL = os.getenv("PAYMENTS_SERVICE_URL", "http://localhost:8003")


class CheckoutItem(BaseModel):
    item_id: str
    quantity: int
    unit_price: float


class CheckoutRequest(BaseModel):
    items: list[CheckoutItem]
    customer_id: str = "cust_mayank"


@app.get("/health")
def health():
    return {"status": "ok", "service": "gateway"}


@app.post("/checkout")
async def checkout(req: CheckoutRequest):
    total_amount = sum(item.quantity * item.unit_price for item in req.items)
    logger.info(
        "checkout_initiated", items_count=len(req.items), total_amount=total_amount
    )

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Step 1: Call Orders Service to create order
        try:
            order_resp = await client.post(
                f"{ORDERS_SERVICE_URL}/orders",
                json={
                    "items": [item.dict() for item in req.items],
                    "total_amount": total_amount,
                    "customer_id": req.customer_id,
                },
            )
            if order_resp.status_code != 200:
                logger.error(
                    "order_creation_failed",
                    status=order_resp.status_code,
                    body=order_resp.text,
                )
                raise HTTPException(
                    status_code=order_resp.status_code,
                    detail=f"Orders service error: {order_resp.text}",
                )
            order_data = order_resp.json()
            order_id = order_data["order_id"]
        except httpx.RequestError as exc:
            logger.error("gateway_cannot_reach_orders", error=str(exc))
            raise HTTPException(
                status_code=503, detail="Gateway cannot reach Orders Service"
            )

        # Step 2: Call Payments Service to process payment
        try:
            payment_resp = await client.post(
                f"{PAYMENTS_SERVICE_URL}/payments/charge",
                json={
                    "order_id": order_id,
                    "amount": total_amount,
                    "currency": "USD",
                    "customer_id": req.customer_id,
                },
            )
            if payment_resp.status_code != 200:
                logger.error(
                    "payment_processing_failed",
                    status=payment_resp.status_code,
                    body=payment_resp.text,
                )
                raise HTTPException(
                    status_code=payment_resp.status_code,
                    detail=f"Payments service error: {payment_resp.text}",
                )
            payment_data = payment_resp.json()
        except httpx.RequestError as exc:
            logger.error("gateway_cannot_reach_payments", error=str(exc))
            raise HTTPException(
                status_code=503, detail="Gateway cannot reach Payments Service"
            )

    logger.info(
        "checkout_completed_successfully",
        order_id=order_id,
        tx_id=payment_data.get("tx_id"),
    )
    return {
        "status": "completed",
        "order_id": order_id,
        "payment": payment_data,
        "total_amount": total_amount,
    }


@app.get("/orders/{order_id}")
async def get_order(order_id: str):
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.get(f"{ORDERS_SERVICE_URL}/orders/{order_id}")
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
            return resp.json()
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=503, detail=f"Gateway cannot reach Orders Service: {exc}"
            )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
