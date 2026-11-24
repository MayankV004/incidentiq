import os
import time
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from incidentiq.agents.graph import incident_graph
from incidentiq.api.main import INCIDENTS_DB, app, run_incident_workflow
from incidentiq.api.security import get_api_key
from incidentiq.schemas.models import Alert

client = TestClient(app)


def test_diagnosis_summary_contains_real_category():
    """CR-01: Asserts the SSE event and diagnosis summary contain the real category, not None."""
    scenarios = [
        ("001_orders_db_pool_exhaustion", "orders", "db_pool_exhaustion"),
        ("002_payments_dependency_timeout", "payments", "dependency_timeout"),
        ("004_gateway_memory_leak", "gateway", "memory_leak"),
    ]

    for scenario_id, service, expected_category in scenarios:
        os.environ["DATA_MODE"] = "replay"
        os.environ["SCENARIO_ID"] = scenario_id

        alert = Alert(
            service=service,
            symptom=f"Telemetry failure on {service}",
            window_start=datetime.now(UTC).isoformat(),
            window_end=datetime.now(UTC).isoformat(),
        )

        state = {
            "incident_id": f"inc_diag_{scenario_id}",
            "alert": alert,
            "plan": [],
            "evidence": [],
            "hypothesis": None,
            "guardrail_flags": [],
            "approval": None,
            "cost_usd": 0.0,
            "steps": 0,
        }

        res = incident_graph.invoke(state)
        hyp = res.get("hypothesis")
        assert hyp is not None
        assert hyp.category == expected_category
        assert hyp.category in ("db_pool_exhaustion", "dependency_timeout", "memory_leak")


def test_list_incidents_contains_category_and_root_cause_for_three_faults():
    """CR-01: Asserts list_incidents endpoint returns real category across 3 different fault types."""
    headers = {"X-API-Key": get_api_key()}
    scenarios = [
        ("001_orders_db_pool_exhaustion", "orders", "db_pool_exhaustion"),
        ("002_payments_dependency_timeout", "payments", "dependency_timeout"),
        ("004_gateway_memory_leak", "gateway", "memory_leak"),
    ]

    for scenario_id, service, expected_category in scenarios:
        inc_id = f"inc_summary_{scenario_id}"
        alert = Alert(
            service=service,
            symptom=f"Telemetry failure on {service}",
            window_start=datetime.now(UTC).isoformat(),
            window_end=datetime.now(UTC).isoformat(),
        )
        INCIDENTS_DB[inc_id] = {
            "incident_id": inc_id,
            "scenario_id": scenario_id,
            "alert": alert.model_dump(),
            "status": "queued",
            "created_at": time.time(),
            "events": [],
        }
        run_incident_workflow(inc_id, alert)

        resp = client.get(f"/v1/incidents/{inc_id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("hypothesis") is not None
        assert data["hypothesis"]["category"] == expected_category
        # Ensure root_cause is not 'None' in summary events
        hypothesis_events = [
            e for e in data.get("events", []) if e.get("type") == "hypothesis_synthesized"
        ]
        assert len(hypothesis_events) == 1
        assert f"Diagnosis: {expected_category}" in hypothesis_events[0]["summary"]
        assert "Diagnosis: None" not in hypothesis_events[0]["summary"]
