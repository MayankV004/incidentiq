import time

from fastapi.testclient import TestClient

from incidentiq.api.main import INCIDENTS_DB, app
from incidentiq.api.security import get_api_key, reset_rate_limits_for_testing
from incidentiq.db.repository import get_incident_from_db

client = TestClient(app)
AUTH_HEADERS = {"X-API-Key": get_api_key()}


def setup_function():
    reset_rate_limits_for_testing()


def test_v1_routes_require_api_key():
    """AUD-03: Asserts unauthenticated /v1/ calls return 401 with standard error shape."""
    # 1. Missing API Key
    res_missing = client.get("/v1/scenarios")
    assert res_missing.status_code == 401
    err_missing = res_missing.json()
    assert "error" in err_missing
    assert err_missing["error"]["code"] == "UNAUTHORIZED"

    # 2. Invalid API Key
    res_invalid = client.get("/v1/scenarios", headers={"X-API-Key": "invalid_wrong_key"})
    assert res_invalid.status_code == 401
    err_invalid = res_invalid.json()
    assert err_invalid["error"]["code"] == "UNAUTHORIZED"

    # 3. Valid API Key succeeds
    res_valid = client.get("/v1/scenarios", headers=AUTH_HEADERS)
    assert res_valid.status_code == 200


def test_health_and_readiness_routes_unauthenticated():
    """AUD-03: /health, /healthz, and /readyz must stay unauthenticated for k8s/monitoring."""
    for path in ("/health", "/healthz", "/readyz"):
        res = client.get(path)
        assert res.status_code == 200
        assert "status" in res.json()


def test_rate_limiting_on_incident_creation():
    """AUD-03: Rate limits POST /v1/incidents to 5 requests per minute per IP."""
    payload = {
        "service": "orders",
        "symptom": "Test symptom for rate limit",
    }

    # 5 requests succeed
    for _ in range(5):
        res = client.post("/v1/incidents", json=payload, headers=AUTH_HEADERS)
        assert res.status_code == 202

    # 6th request triggers 429
    res_limited = client.post("/v1/incidents", json=payload, headers=AUTH_HEADERS)
    assert res_limited.status_code == 429
    data = res_limited.json()
    assert data["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    assert data["error"]["details"]["limit"] == 5


def test_rate_limiting_on_reads():
    """AUD-03: Rate limits GET /v1/* to 30 requests per minute per IP."""
    for _ in range(30):
        res = client.get("/v1/scenarios", headers=AUTH_HEADERS)
        assert res.status_code == 200

    # 31st request triggers 429
    res_limited = client.get("/v1/scenarios", headers=AUTH_HEADERS)
    assert res_limited.status_code == 429
    data = res_limited.json()
    assert data["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    assert data["error"]["details"]["limit"] == 30


def test_daily_cost_cap_enforcement():
    """AUD-03: Asserts exceeding the daily cost cap returns 429 BUDGET_EXCEEDED."""
    # Temporarily insert an incident with high spend today
    mock_id = f"test_cap_drain_{int(time.time())}"
    INCIDENTS_DB[mock_id] = {
        "incident_id": mock_id,
        "status": "completed",
        "cost_usd": 2.50,  # exceeds default daily cap of $2.00
        "created_at": time.time(),
        "alert": {"service": "orders", "symptom": "mock drain"},
    }

    payload = {"service": "orders", "symptom": "Blocked by daily budget"}
    res = client.post("/v1/incidents", json=payload, headers=AUTH_HEADERS)
    assert res.status_code == 429
    data = res.json()
    assert data["error"]["code"] == "BUDGET_EXCEEDED"
    assert data["error"]["details"]["daily_cost_cap_usd"] == 2.00

    # Cleanup mock incident
    INCIDENTS_DB.pop(mock_id, None)


def test_pii_redacted_before_persistence_and_raw_alert():
    """AUD-04: PII must be redacted before anything is persisted to DB or queued."""
    raw_email = "victim.user@example.com"
    raw_phone = "555-987-6543"
    raw_card = "4532-1234-5678-9012"
    symptom_with_pii = f"Payment failure for {raw_email} phone {raw_phone} card {raw_card}"

    payload = {
        "service": "payments",
        "symptom": symptom_with_pii,
    }

    res = client.post("/v1/incidents", json=payload, headers=AUTH_HEADERS)
    assert res.status_code == 202
    incident_id = res.json()["incident_id"]

    # 1. Inspect in-memory state
    mem_alert = INCIDENTS_DB[incident_id]["alert"]["symptom"]
    assert "[REDACTED_EMAIL]" in mem_alert
    assert "[REDACTED_PHONE]" in mem_alert
    assert "[REDACTED_CARD]" in mem_alert
    assert raw_email not in mem_alert
    assert raw_phone not in mem_alert
    assert raw_card not in mem_alert

    # 2. Inspect persistent database record directly
    db_record = get_incident_from_db(incident_id)
    assert db_record is not None
    db_symptom = db_record["alert"]["symptom"]
    assert "[REDACTED_EMAIL]" in db_symptom
    assert "[REDACTED_PHONE]" in db_symptom
    assert "[REDACTED_CARD]" in db_symptom
    assert raw_email not in db_symptom
    assert raw_phone not in db_symptom
    assert raw_card not in db_symptom
