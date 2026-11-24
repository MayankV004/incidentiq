from datetime import UTC, datetime

from incidentiq.agents.graph import incident_graph, route_specialist_fanout
from incidentiq.agents.nodes import supervisor_node
from incidentiq.schemas.models import Alert


def test_supervisor_deterministic_planner():
    now = datetime.now(UTC).isoformat()
    alert = Alert(service="orders", symptom="500 errors", window_start=now, window_end=now)

    state = {
        "incident_id": "test-sup-1",
        "alert": alert,
        "raw_alert": "orders 500 errors",
    }
    result = supervisor_node(state)
    assert "plan" in result
    assert isinstance(result["plan"], list)
    assert set(result["plan"]) == {"metrics", "logs", "runbook"}
    assert result["cost_usd"] == 0.0
    assert result["steps"] == 1


def test_route_specialist_fanout():
    assert route_specialist_fanout({"plan": ["metrics"]}) == ["metrics_agent"]
    assert route_specialist_fanout({"plan": ["logs", "runbook"]}) == ["logs_agent", "runbook_agent"]
    assert route_specialist_fanout({"plan": ["metrics", "logs", "runbook"]}) == [
        "metrics_agent",
        "logs_agent",
        "runbook_agent",
    ]
    # Default fallback when plan empty
    assert route_specialist_fanout({}) == ["metrics_agent", "logs_agent", "runbook_agent"]


def test_graph_executes_driven_by_supervisor_plan():
    now = datetime.now(UTC).isoformat()
    alert = Alert(service="orders", symptom="500 Internal Server Error", window_start=now, window_end=now)

    res = incident_graph.invoke(
        {
            "alert": alert,
            "incident_id": "test-sup-graph",
            "raw_alert": "orders 500 error",
        }
    )
    assert res.get("hypothesis") is not None
    assert "metrics" in res.get("plan", [])

