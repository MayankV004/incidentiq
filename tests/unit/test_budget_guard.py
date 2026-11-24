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


def test_budget_and_thresholds_configured_via_env(monkeypatch):
    """BLOCKER-6: MAX_AGENT_STEPS, INCIDENT_BUDGET_USD, ABSTAIN_THRESHOLD, and GROUND_THRESHOLD read from env."""
    from incidentiq.agents.nodes import output_guard_node
    from incidentiq.schemas.models import Evidence

    monkeypatch.setenv("MAX_AGENT_STEPS", "3")
    monkeypatch.setenv("INCIDENT_BUDGET_USD", "0.01")
    assert check_budget_exceeded({"steps": 3, "cost_usd": 0.001}) is True
    assert check_budget_exceeded({"steps": 1, "cost_usd": 0.01}) is True
    assert check_budget_exceeded({"steps": 2, "cost_usd": 0.005}) is False

    monkeypatch.setenv("ABSTAIN_THRESHOLD", "0.90")
    monkeypatch.setenv("GROUND_THRESHOLD", "0.95")

    ev1 = Evidence(id="ev_1", kind="metric", summary="m1", source_ref="mcp:1")
    ev2 = Evidence(id="ev_2", kind="log", summary="l1", source_ref="mcp:2")

    # 1. Confidence 0.80 < 0.90 ABSTAIN_THRESHOLD -> abstains
    hyp_low_conf = Hypothesis(
        category="db_pool_exhaustion",
        confidence=0.80,
        reasoning="moderate signal",
        evidence_ids=["ev_1", "ev_2"],
        suggested_action=Action(type="restart_service", target="orders", detail="x"),
        abstained=False,
    )
    out1 = output_guard_node(
        {"hypothesis": hyp_low_conf, "evidence": [ev1, ev2]}
    )
    assert out1["hypothesis"].abstained is True

    # 2. 1 of 2 evidence IDs invalid -> groundedness 0.5 < 0.95 GROUND_THRESHOLD -> abstains
    hyp_low_ground = Hypothesis(
        category="db_pool_exhaustion",
        confidence=0.95,
        reasoning="high conf but ungrounded citation",
        evidence_ids=["ev_1", "ev_fake"],
        suggested_action=Action(type="restart_service", target="orders", detail="x"),
        abstained=False,
    )
    out2 = output_guard_node(
        {"hypothesis": hyp_low_ground, "evidence": [ev1, ev2]}
    )
    assert out2["hypothesis"].abstained is True
