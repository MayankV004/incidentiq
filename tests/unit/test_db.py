import time

from incidentiq.db import init_db
from incidentiq.db.repository import (
    append_event_to_db,
    get_incident_from_db,
    list_incidents_from_db,
    update_incident,
    upsert_incident,
)


def test_database_crud():
    # 1. Initialize schema
    init_db()

    inc_id = f"test_inc_{int(time.time() * 1000)}"
    data = {
        "incident_id": inc_id,
        "scenario_id": "001_orders_db_pool_exhaustion",
        "alert": {
            "service": "orders",
            "symptom": "DB pool exhausted",
            "window_start": "2026-11-24T12:00:00Z",
            "window_end": "2026-11-24T12:30:00Z",
        },
        "status": "queued",
        "cost_usd": 0.0,
        "latency_ms": 0.0,
        "steps": 0,
        "events": [],
    }

    # 2. Insert
    saved = upsert_incident(data)
    assert saved["incident_id"] == inc_id
    assert saved["status"] == "queued"
    assert saved["alert"]["service"] == "orders"

    # 3. Append Event
    ev = {"id": "ev_test_1", "type": "incident_started", "node": "system"}
    append_event_to_db(inc_id, ev)

    # 4. Update status & hypothesis
    updated = update_incident(
        inc_id,
        {
            "status": "awaiting_approval",
            "cost_usd": 0.0045,
            "latency_ms": 6.2,
            "hypothesis": {"category": "db_pool_exhaustion", "confidence": 0.85},
        },
    )
    assert updated is not None
    assert updated["status"] == "awaiting_approval"
    assert updated["cost_usd"] == 0.0045

    # 5. Get from DB
    fetched = get_incident_from_db(inc_id)
    assert fetched is not None
    assert fetched["status"] == "awaiting_approval"
    assert len(fetched["events"]) == 1
    assert fetched["hypothesis"]["category"] == "db_pool_exhaustion"

    # 6. List from DB
    all_incidents = list_incidents_from_db()
    assert any(i["incident_id"] == inc_id for i in all_incidents)
