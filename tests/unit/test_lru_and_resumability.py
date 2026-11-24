import os
import time

import pytest
from fastapi.testclient import TestClient

from incidentiq.api.main import INCIDENTS_DB, app
from incidentiq.api.security import get_api_key
from incidentiq.db.cache import IncidentLRUCache, check_single_worker
from incidentiq.db.repository import upsert_incident
from incidentiq.security.tokens import _SERVER_APPROVAL_TOKENS


def test_lru_cache_eviction_and_db_fallback():
    """Task 6: Tests that LRU cache evicts oldest and falls back to database lookup."""
    cache = IncidentLRUCache(capacity=2)

    inc1 = {
        "incident_id": "test_lru_1",
        "status": "completed",
        "created_at": time.time(),
        "alert": {"service": "orders", "symptom": "s1"},
    }
    inc2 = {
        "incident_id": "test_lru_2",
        "status": "completed",
        "created_at": time.time(),
        "alert": {"service": "payments", "symptom": "s2"},
    }
    inc3 = {
        "incident_id": "test_lru_3",
        "status": "completed",
        "created_at": time.time(),
        "alert": {"service": "gateway", "symptom": "s3"},
    }

    # Pre-save inc1 to DB so it can be re-fetched after eviction
    upsert_incident(inc1)

    cache.set("test_lru_1", inc1)
    cache.set("test_lru_2", inc2)
    assert len(cache) == 2

    # Inserting 3rd item should evict inc1 from in-memory cache
    cache.set("test_lru_3", inc3)
    assert len(cache) == 2
    assert "test_lru_1" not in cache._cache

    # Getting inc1 should trigger database fallback
    fetched = cache.get("test_lru_1")
    assert fetched is not None
    assert fetched["incident_id"] == "test_lru_1"
    assert "test_lru_1" in cache._cache


def test_single_worker_enforcement():
    """Task 6: Tests that check_single_worker raises RuntimeError if concurrency > 1."""
    old_conc = os.environ.get("WEB_CONCURRENCY")
    try:
        os.environ["WEB_CONCURRENCY"] = "2"
        with pytest.raises(RuntimeError) as exc_info:
            check_single_worker()
        assert "Single-worker mode" in str(exc_info.value)

        os.environ["WEB_CONCURRENCY"] = "1"
        check_single_worker()  # Should not raise
    finally:
        if old_conc is not None:
            os.environ["WEB_CONCURRENCY"] = old_conc
        else:
            os.environ.pop("WEB_CONCURRENCY", None)


def test_awaiting_approval_resumable_after_restart():
    """Task 6: Tests that awaiting_approval incidents resume and approve cleanly after full restart."""
    client = TestClient(app)
    inc_id = "test_restart_resumable_inc"
    appr_id = "appr_req_restart_99"

    inc_data = {
        "incident_id": inc_id,
        "scenario_id": "001_orders_db_pool_exhaustion",
        "alert": {"service": "orders", "symptom": "pool exhausted"},
        "status": "awaiting_approval",
        "approval": {
            "approval_id": appr_id,
            "status": "awaiting_approval",
            "action": {
                "type": "restart_service",
                "target": "orders",
                "detail": "Restart orders service container",
            },
        },
        "created_at": time.time(),
        "events": [],
    }

    # Save to persistent database
    upsert_incident(inc_data)

    # Simulate complete server restart: clear memory cache and in-memory tokens
    INCIDENTS_DB.clear()
    _SERVER_APPROVAL_TOKENS.clear()
    assert inc_id not in INCIDENTS_DB._cache
    assert appr_id not in _SERVER_APPROVAL_TOKENS

    headers = {"X-API-Key": get_api_key()}

    # Approve the incident after restart
    resp = client.post(
        f"/v1/incidents/{inc_id}/approval",
        json={"decision": "approve", "approval_id": appr_id},
        headers=headers,
    )

    assert resp.status_code == 200, (
        f"Expected 200 but got {resp.status_code}: {resp.text}"
    )
    data = resp.json()
    assert data["status"] == "approved_and_executed"
    assert data["result"]["action"] == "restart_service"
