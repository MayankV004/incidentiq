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
    res_invalid = client.get(
        "/v1/scenarios", headers={"X-API-Key": "invalid_wrong_key"}
    )
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
    symptom_with_pii = (
        f"Payment failure for {raw_email} phone {raw_phone} card {raw_card}"
    )

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


def test_approval_conflict_returns_409_and_standard_error_shape():
    """AUD-12: Approving an incident not awaiting approval returns 409 in standard error shape."""
    mock_id = f"test_inc_conflict_{int(time.time())}"
    INCIDENTS_DB[mock_id] = {
        "incident_id": mock_id,
        "status": "running",  # not awaiting_approval
        "approval": None,
    }

    payload = {
        "decision": "approve",
        "approval_id": "appr_req_fake",
    }
    res = client.post(
        f"/v1/incidents/{mock_id}/approval", json=payload, headers=AUTH_HEADERS
    )
    assert res.status_code == 409
    data = res.json()
    assert "error" in data
    assert data["error"]["code"] == "STATE_CONFLICT"
    assert "not awaiting approval" in data["error"]["message"].lower()

    # Clean up
    INCIDENTS_DB.pop(mock_id, None)


def test_missing_secrets_fail_fast_at_startup(monkeypatch):
    """BLOCKER-2: API and remediation server must have no default secret fallbacks and fail fast if unset."""
    import pytest

    import incidentiq.api.security as api_sec
    import incidentiq.security.tokens as sec_tokens
    from mcp_servers.remediation.server import app as remediation_app

    assert not hasattr(api_sec, "DEFAULT_API_KEY")
    assert not hasattr(sec_tokens, "DEFAULT_APPROVAL_SECRET")

    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("APPROVAL_TOKEN_SECRET", raising=False)

    with pytest.raises(RuntimeError), TestClient(app):
        pass

    monkeypatch.setenv("API_KEY", "fake_test_key")
    with pytest.raises(RuntimeError), TestClient(app):
        pass

    with pytest.raises(RuntimeError), TestClient(remediation_app):
        pass


def test_extract_client_ip_trusts_only_configured_proxies(monkeypatch):
    """BLOCKER-5: Trust X-Forwarded-For only from trusted proxy IPs, resisting client spoofing."""
    from starlette.requests import Request

    from incidentiq.api.security import extract_client_ip

    monkeypatch.setenv("TRUSTED_PROXY_IPS", "172.16.0.0/12,127.0.0.1")

    def make_req(peer_ip: str, xff: str | None = None) -> Request:
        headers = []
        if xff is not None:
            headers.append((b"x-forwarded-for", xff.encode("latin-1")))
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/v1/scenarios",
            "headers": headers,
            "client": (peer_ip, 12345),
        }
        return Request(scope)

    # 1. From trusted proxy: extract rightmost non-proxy client IP (ignores attacker spoof on left)
    assert extract_client_ip(make_req("172.18.0.5", "9.9.9.9, 203.0.113.42")) == "203.0.113.42"
    # 2. From trusted proxy with single IP: returns that client IP
    assert extract_client_ip(make_req("127.0.0.1", "198.51.100.7")) == "198.51.100.7"
    # 3. From untrusted direct peer: ignores X-Forwarded-For completely
    assert extract_client_ip(make_req("198.51.100.88", "1.2.3.4")) == "198.51.100.88"


def test_daily_cost_cap_persists_across_restart():
    """BLOCKER-6: Daily spend calculation must query persisted DB records across in-memory cache clears."""
    from incidentiq.db.models import IncidentRecord
    from incidentiq.db.repository import upsert_incident
    from incidentiq.db.session import SessionLocal

    mock_id = f"test_db_cap_{int(time.time())}"
    upsert_incident(
        {
            "incident_id": mock_id,
            "status": "completed",
            "cost_usd": 2.50,
            "created_at": time.time(),
            "alert": {"service": "orders", "symptom": "db persisted drain"},
        }
    )
    # Simulate API restart where completed incidents are NOT in INCIDENTS_DB cache
    INCIDENTS_DB.clear()

    try:
        res = client.post(
            "/v1/incidents",
            json={"service": "orders", "symptom": "Should be blocked by persisted DB cap"},
            headers=AUTH_HEADERS,
        )
        assert res.status_code == 429
        assert res.json()["error"]["code"] == "BUDGET_EXCEEDED"
    finally:
        INCIDENTS_DB.pop(mock_id, None)
        with SessionLocal() as db:
            db.query(IncidentRecord).filter(IncidentRecord.id == mock_id).delete()
            db.commit()


def test_sse_stream_terminates_on_budget_exceeded():
    """BLOCKER-6: GET /v1/incidents/{id}/stream must return cleanly when status == budget_exceeded."""
    mock_id = f"test_sse_budget_{int(time.time())}"
    INCIDENTS_DB[mock_id] = {
        "incident_id": mock_id,
        "status": "budget_exceeded",
        "cost_usd": 0.06,
        "created_at": time.time(),
        "alert": {"service": "orders", "symptom": "budget drain"},
        "events": [
            {
                "id": "ev_done",
                "type": "done",
                "node": "system",
                "title": "Stopped",
                "summary": "Budget exceeded",
                "status": "budget_exceeded",
                "timestamp": time.time(),
            }
        ],
    }
    try:
        res = client.get(f"/v1/incidents/{mock_id}/stream", headers=AUTH_HEADERS)
        assert res.status_code == 200
        assert "budget_exceeded" in res.text
    finally:
        INCIDENTS_DB.pop(mock_id, None)


def test_create_incident_input_validation_returns_400():
    """BLOCKER-7: Invalid service, scenario_id, symptom, or window_end <= window_start must return 400."""
    bad_payloads = [
        {"service": "payments' OR 1=1; --", "symptom": "high latency"},
        {"service": "orders", "symptom": "high latency", "scenario_id": "../../etc/passwd"},
        {"service": "orders", "symptom": "   "},
        {
            "service": "orders",
            "symptom": "high latency",
            "window_start": "2026-11-24T12:30:00Z",
            "window_end": "2026-11-24T12:00:00Z",
        },
    ]
    for payload in bad_payloads:
        res = client.post("/v1/incidents", json=payload, headers=AUTH_HEADERS)
        assert res.status_code == 400, f"Expected 400 for {payload}, got {res.status_code}"
        data = res.json()
        assert "error" in data and data["error"]["code"] == "INVALID_INPUT"


def test_expanded_pii_and_prompt_leakage_blocking(monkeypatch):
    """BLOCKER-7: Expand PII scrubbing (service+symptom) and block prompt/secret leaks in output_guard_node."""
    from incidentiq.agents.nodes import output_guard_node
    from incidentiq.guardrails.guards import GuardrailManager
    from incidentiq.schemas.models import Action, Alert, Evidence, Hypothesis

    raw_alert = Alert(
        service="orders (555) 123-4567",
        symptom="User SSN 123-45-6789 leaked Bearer tok_secret12345 and sk-abcdef1234567890",
        window_start="2026-11-24T12:00:00Z",
        window_end="2026-11-24T12:30:00Z",
    )
    clean_alert, flags = GuardrailManager.process_input_alert(raw_alert)
    assert "(555)" not in clean_alert.service
    assert "123-45-6789" not in clean_alert.symptom
    assert "tok_secret12345" not in clean_alert.symptom
    assert "sk-abcdef1234567890" not in clean_alert.symptom
    assert "pii_redacted_in_alert" in flags

    monkeypatch.setenv("API_KEY", "super_secret_demo_key_999")
    ev = Evidence(id="ev_1", kind="metric", summary="m1", source_ref="mcp:1")
    leaked_hyp = Hypothesis(
        category="db_pool_exhaustion",
        confidence=0.95,
        reasoning="Root cause found; leaked secret super_secret_demo_key_999",
        evidence_ids=["ev_1"],
        suggested_action=Action(type="restart_service", target="orders", detail="x"),
        abstained=False,
    )
    out = output_guard_node({"hypothesis": leaked_hyp, "evidence": [ev]})
    assert out["hypothesis"].abstained is True
    assert out["hypothesis"].suggested_action is None
    assert "super_secret_demo_key_999" not in out["hypothesis"].reasoning
    assert any("leak" in f for f in out["guardrail_flags"])


