import os

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from shop.common.telemetry import setup_telemetry

app = FastAPI(title="Shop: Payments Service")
logger = setup_telemetry(app, "payments")

FAKE_EXTERNAL_URL = os.getenv("FAKE_EXTERNAL_URL", "http://localhost:8004")
CLIENT_TIMEOUT_SEC = float(os.getenv("PAYMENTS_TIMEOUT_SEC", "5.0"))


class PaymentRequest(BaseModel):
    order_id: str
    amount: float
    currency: str = "USD"
    customer_id: str = "cust_default"


@app.get("/health")
def health():
    return {"status": "ok", "service": "payments"}


@app.post("/payments/charge")
async def process_payment(req: PaymentRequest):
    logger.info("processing_payment_request", order_id=req.order_id, amount=req.amount)

    async with httpx.AsyncClient(timeout=CLIENT_TIMEOUT_SEC) as client:
        try:
            resp = await client.post(
                f"{FAKE_EXTERNAL_URL}/charge",
                json={
                    "amount": req.amount,
                    "currency": req.currency,
                    "customer_id": req.customer_id,
                },
            )
            if resp.status_code != 200:
                logger.error("external_payment_failed", status_code=resp.status_code, body=resp.text)
                raise HTTPException(
                    status_code=502,
                    detail=f"Downstream payment gateway error: {resp.text}",
                )

            data = resp.json()
            return {
                "status": "paid",
                "order_id": req.order_id,
                "tx_id": data.get("tx_id"),
                "amount": req.amount,
            }

        except httpx.TimeoutException as exc:
            logger.error("external_payment_timeout", error=str(exc))
            raise HTTPException(
                status_code=504,
                detail="Payment gateway connection timed out",
            )
        except httpx.RequestError as exc:
            logger.error("external_payment_connection_refused", error=str(exc))
            raise HTTPException(
                status_code=503,
                detail=f"Unable to reach payment provider: {exc}",
            )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
