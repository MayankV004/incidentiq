import time
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from incidentiq.api.main import INCIDENTS_DB, app, run_incident_workflow
from incidentiq.api.security import get_api_key
from incidentiq.schemas.models import Alert
from incidentiq.security.tokens import (
    generate_capability_token,
    reset_consumed_tokens_for_testing,
    verify_capability_token,
)
from mcp_servers.remediation.server import restart_service, rollback_deploy


def setup_function():
    reset_consumed_tokens_for_testing()


def test_valid_capability_token_execution():
    """Asserts that a valid HMAC token authorizes dry-run remediation."""
    token = generate_capability_token(
        incident_id="inc_001",
        action="restart_service",
        target="orders",
        ttl_seconds=900,
    )
    res = restart_service("orders", token=token, incident_id="inc_001")
    assert res["success"] is True
    assert res["status"] == "dry_run_success"
    assert "orders" in res["message"]


def test_forged_capability_token_rejected():
    """Asserts that a forged token or signature alteration fails verification."""
    token = generate_capability_token(
        incident_id="inc_001",
        action="restart_service",
        target="orders",
    )
    parts = token.split(".")
    forged_token = parts[0] + "." + ("0" * len(parts[1]))

    valid, reason = verify_capability_token(forged_token)
    assert valid is False
    assert "FORGED_TOKEN" in reason

    res = restart_service("orders", token=forged_token, incident_id="inc_001")
    assert res["success"] is False
    assert "UNAUTHORIZED_ACTION" in res["error"]


def test_wrong_incident_binding_rejected():
    """Asserts that a token bound to incident A cannot be used on incident B."""
    token = generate_capability_token(
        incident_id="inc_alpha",
        action="restart_service",
        target="orders",
    )
    valid, reason = verify_capability_token(
        token=token,
        expected_incident_id="inc_beta",
        expected_action="restart_service",
        expected_target="orders",
    )
    assert valid is False
    assert "WRONG_INCIDENT" in reason


def test_wrong_action_binding_rejected():
    """Asserts that a token issued for restart_service cannot execute rollback_deploy."""
    token = generate_capability_token(
        incident_id="inc_001",
        action="restart_service",
        target="orders",
    )
    valid, reason = verify_capability_token(
        token=token,
        expected_action="rollback_deploy",
        expected_target="orders",
    )
    assert valid is False
    assert "WRONG_ACTION" in reason

    res = rollback_deploy("orders", target_version="v1.0", token=token, incident_id="inc_001")
    assert res["success"] is False
    assert "WRONG_ACTION" in res["error"]


def test_wrong_target_service_binding_rejected():
    """Asserts that a token issued for 'orders' cannot be applied to 'payments'."""
    token = generate_capability_token(
        incident_id="inc_001",
        action="restart_service",
        target="orders",
    )
    res = restart_service("payments", token=token, incident_id="inc_001")
    assert res["success"] is False
    assert "WRONG_TARGET" in res["error"]


def test_expired_capability_token_rejected():
    """Asserts that a token past its 15-minute validity window is rejected."""
    expired_token = generate_capability_token(
        incident_id="inc_001",
        action="restart_service",
        target="orders",
        ttl_seconds=-10,  # expired 10 seconds ago
    )
    valid, reason = verify_capability_token(expired_token)
    assert valid is False
    assert "EXPIRED_TOKEN" in reason


def test_reused_capability_token_rejected():
    """Asserts that single-use tokens cannot be replayed."""
    token = generate_capability_token(
        incident_id="inc_001",
        action="restart_service",
        target="orders",
    )
    # First call succeeds and consumes token
    res1 = restart_service("orders", token=token, incident_id="inc_001")
    assert res1["success"] is True

    # Replay call fails
    res2 = restart_service("orders", token=token, incident_id="inc_001")
    assert res2["success"] is False
    assert "REPLAY_DETECTED" in res2["error"]


def test_missing_secret_fails_safely():
    """Asserts that empty secret safely refuses verification without throwing uncaught exceptions."""
    token = generate_capability_token(
        incident_id="inc_001",
        action="restart_service",
        target="orders",
    )
    valid, reason = verify_capability_token(token, secret="")
    assert valid is False
    assert "MISSING_SECRET" in reason


def test_raw_token_never_exposed_in_sse_or_rest():
    """AUD-02: Asserts raw capability tokens never leak in SSE streams or REST responses."""
    client = TestClient(app)

    # 1. Run investigation directly to awaiting_approval
    alert = Alert(
        service="orders",
        symptom="DB connection pool exhausted: too many connections",
        window_start=datetime.now(UTC).isoformat(),
        window_end=datetime.now(UTC).isoformat(),
    )
    inc_id = "test_inc_leak_check"
    INCIDENTS_DB[inc_id] = {
        "incident_id": inc_id,
        "scenario_id": "001_orders_db_pool_exhaustion",
        "alert": alert.model_dump(),
        "status": "queued",
        "created_at": time.time(),
        "events": [],
    }

    run_incident_workflow(inc_id, alert)

    headers = {"X-API-Key": get_api_key()}

    # 2. Check REST GET /v1/incidents/{id}
    resp = client.get(f"/v1/incidents/{inc_id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    resp_str = resp.text
    # Neither raw token prefix nor cap_ nor hash should appear in raw view
    assert "cap_" not in resp_str
    assert "token_hash" not in resp_str
    assert "approval_token" not in resp_str

    # Only approval_id should be present
    assert "approval" in data
    assert "approval_id" in data["approval"]
    approval_id = data["approval"]["approval_id"]
    assert approval_id.startswith("appr_req_")

    # 3. Check SSE stream output for raw capability token leak
    stream_resp = client.get(f"/v1/incidents/{inc_id}/stream", headers=headers)
    assert stream_resp.status_code == 200
    stream_text = stream_resp.text

    assert "cap_" not in stream_text
    assert "token_hash" not in stream_text
    assert "approval_token" not in stream_text

    # 4. Engineer approves using approval_id
    appr_resp = client.post(
        f"/v1/incidents/{inc_id}/approval",
        json={"decision": "approve", "approval_id": approval_id},
        headers=headers,
    )
    assert appr_resp.status_code == 200
    assert appr_resp.json()["status"] == "approved_and_executed"
