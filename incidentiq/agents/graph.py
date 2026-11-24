import os

from langgraph.graph import END, START, StateGraph

from incidentiq.agents.nodes import (
    budget_exceeded_node,
    human_approval_node,
    input_guard_node,
    logs_agent_node,
    metrics_agent_node,
    output_guard_node,
    report_node,
    root_cause_agent_node,
    runbook_agent_node,
    supervisor_node,
)
from incidentiq.agents.state import IncidentState

MAX_AGENT_STEPS = 12
INCIDENT_BUDGET_USD = 0.05


def get_max_agent_steps() -> int:
    try:
        return int(os.getenv("MAX_AGENT_STEPS", str(MAX_AGENT_STEPS)))
    except ValueError:
        return MAX_AGENT_STEPS


def get_incident_budget_usd() -> float:
    try:
        return float(os.getenv("INCIDENT_BUDGET_USD", str(INCIDENT_BUDGET_USD)))
    except ValueError:
        return INCIDENT_BUDGET_USD


def check_budget_exceeded(state: IncidentState) -> bool:
    """Checks whether current incident has exhausted step or cost allocations."""
    steps = state.get("steps", 0)
    cost_usd = state.get("cost_usd", 0.0)
    return bool(
        steps >= get_max_agent_steps() or cost_usd >= get_incident_budget_usd()
    )


def route_specialist_fanout(state: IncidentState) -> list[str]:
    """Dynamically fans out from supervisor to specialists driven by supervisor's plan."""
    plan = state.get("plan", [])
    destinations = []
    if "metrics" in plan:
        destinations.append("metrics_agent")
    if "logs" in plan:
        destinations.append("logs_agent")
    if "runbook" in plan:
        destinations.append("runbook_agent")
    return destinations or ["metrics_agent", "logs_agent", "runbook_agent"]


def route_after_output_guard(state: IncidentState) -> str:
    """Routes to budget_exceeded if limits hit, human approval if an action is proposed, otherwise report."""
    if check_budget_exceeded(state):
        return "budget_exceeded"

    hypothesis = state.get("hypothesis")
    if (
        hypothesis
        and not hypothesis.abstained
        and hypothesis.suggested_action
        and hypothesis.suggested_action.type != "none"
    ):
        return "human_approval"
    return "report"


def build_incident_graph() -> StateGraph:
    """Builds the LangGraph multi-agent orchestration state machine."""
    workflow = StateGraph(IncidentState)

    # 1. Add all functional agent & guard nodes
    workflow.add_node("input_guard", input_guard_node)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("metrics_agent", metrics_agent_node)
    workflow.add_node("logs_agent", logs_agent_node)
    workflow.add_node("runbook_agent", runbook_agent_node)
    workflow.add_node("root_cause_agent", root_cause_agent_node)
    workflow.add_node("output_guard", output_guard_node)
    workflow.add_node("budget_exceeded", budget_exceeded_node)
    workflow.add_node("human_approval", human_approval_node)
    workflow.add_node("report", report_node)

    # 2. Build edges: Input guard -> Supervisor
    workflow.add_edge(START, "input_guard")
    workflow.add_edge("input_guard", "supervisor")

    # 3. Dynamic Parallel Fan-Out: Supervisor plan directly drives specialist dispatch
    workflow.add_conditional_edges(
        "supervisor",
        route_specialist_fanout,
        ["metrics_agent", "logs_agent", "runbook_agent"],
    )

    # 4. Parallel Fan-In: All three specialists merge evidence into Root-Cause Agent
    workflow.add_edge("metrics_agent", "root_cause_agent")
    workflow.add_edge("logs_agent", "root_cause_agent")
    workflow.add_edge("runbook_agent", "root_cause_agent")

    # 5. Root Cause -> Output Guard -> Conditional Routing
    workflow.add_edge("root_cause_agent", "output_guard")
    workflow.add_conditional_edges(
        "output_guard",
        route_after_output_guard,
        {
            "budget_exceeded": "budget_exceeded",
            "human_approval": "human_approval",
            "report": "report",
        },
    )
    workflow.add_edge("budget_exceeded", "report")
    workflow.add_edge("human_approval", "report")
    workflow.add_edge("report", END)

    return workflow


# Compiled graph singleton
incident_graph = build_incident_graph().compile()
