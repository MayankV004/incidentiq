import asyncio
import os
import random
import uuid

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from shop.common.telemetry import setup_telemetry

app = FastAPI(title="Shop: Fake External Payment Provider")
logger = setup_telemetry(app, "fake_external")

# Configurable chaos parameters
INJECTED_DELAY_SEC = float(os.getenv("EXTERNAL_DELAY_SEC", "0.0"))
INJECTED_FAILURE_RATE = float(os.getenv("EXTERNAL_FAILURE_RATE", "0.0"))


class ChargeRequest(BaseModel):
    amount: float
    currency: str = "USD"
    customer_id: str = "cust_default"


class ChaosConfig(BaseModel):
    delay_sec: float = 0.0
    failure_rate: float = 0.0


@app.get("/health")
def health():
    return {"status": "ok", "service": "fake_external"}


@app.post("/chaos")
def set_chaos(config: ChaosConfig):
    global INJECTED_DELAY_SEC, INJECTED_FAILURE_RATE
    INJECTED_DELAY_SEC = config.delay_sec
    INJECTED_FAILURE_RATE = config.failure_rate
    logger.info("chaos_updated", delay_sec=INJECTED_DELAY_SEC, failure_rate=INJECTED_FAILURE_RATE)
    return {"status": "updated", "delay_sec": INJECTED_DELAY_SEC, "failure_rate": INJECTED_FAILURE_RATE}


@app.post("/charge")
async def charge(req: ChargeRequest):
    # Simulate network latency if configured
    delay = INJECTED_DELAY_SEC or float(os.getenv("EXTERNAL_DELAY_SEC", "0.0"))
    if delay > 0:
        logger.info("simulating_network_latency", delay_sec=delay)
        await asyncio.sleep(delay)

    # Simulate random or forced failures
    failure_rate = INJECTED_FAILURE_RATE or float(os.getenv("EXTERNAL_FAILURE_RATE", "0.0"))
    if failure_rate > 0 and random.random() < failure_rate:
        logger.error("external_bank_downtime_error", amount=req.amount)
        raise HTTPException(status_code=503, detail="External Payment Gateway 503 Service Unavailable")

    tx_id = f"tx_{uuid.uuid4().hex[:10]}"
    logger.info("charge_processed", tx_id=tx_id, amount=req.amount)
    return {
        "status": "success",
        "tx_id": tx_id,
        "amount": req.amount,
        "currency": req.currency,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
