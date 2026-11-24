from incidentiq.agents.graph import (
    INCIDENT_BUDGET_USD,
    MAX_AGENT_STEPS,
    build_incident_graph,
    check_budget_exceeded,
    route_after_output_guard,
)
from incidentiq.schemas.models import Action, Alert, Hypothesis


def test_check_budget_exceeded():
    assert not check_budget_exceeded({"steps": 5, "cost_usd": 0.01})
    assert check_budget_exceeded({"steps": MAX_AGENT_STEPS, "cost_usd": 0.01})
    assert check_budget_exceeded({"steps": 4, "cost_usd": INCIDENT_BUDGET_USD})


def test_route_after_output_guard_routing():
    action = Action(type="restart_service", target="orders", detail="restart")
    hyp = Hypothesis(
        category="db_pool_exhaustion",
        confidence=0.9,
        reasoning="pool exhausted",
        suggested_action=action,
        abstained=False,
    )

    # Within budget with action -> human_approval
    state_ok = {"steps": 5, "cost_usd": 0.01, "hypothesis": hyp}
    assert route_after_output_guard(state_ok) == "human_approval"

    # Exceeded steps -> budget_exceeded
    state_steps_exceeded = {"steps": 15, "cost_usd": 0.01, "hypothesis": hyp}
    assert route_after_output_guard(state_steps_exceeded) == "budget_exceeded"

    # Exceeded cost -> budget_exceeded
    state_cost_exceeded = {"steps": 5, "cost_usd": 0.08, "hypothesis": hyp}
    assert route_after_output_guard(state_cost_exceeded) == "budget_exceeded"


def test_graph_execution_with_budget_exceeded():
    graph = build_incident_graph().compile()
    alert = Alert(
        service="orders",
        symptom="DB pool exhausted",
        window_start="2026-11-24T12:00:00Z",
        window_end="2026-11-24T12:30:00Z",
    )

    # Force steps to already be high
    init_state = {
        "incident_id": "inc_budget_test",
        "alert": alert,
        "steps": 12,
        "cost_usd": 0.01,
        "evidence": [],
        "guardrail_flags": [],
        "plan": ["metrics", "logs", "runbook"],
    }
    result = graph.invoke(init_state)

    assert "BUDGET_EXCEEDED" in result["guardrail_flags"]
    assert result["hypothesis"].abstained is True
    assert "Budget exceeded" in result["hypothesis"].abstain_reason
    # Ensure no approval token was generated
    assert result.get("approval") is None
