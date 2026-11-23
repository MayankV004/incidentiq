from langgraph.graph import END, START, StateGraph

from incidentiq.agents.nodes import (
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


def route_after_output_guard(state: IncidentState) -> str:
    """Routes to human approval if an action is proposed, otherwise straight to report."""
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
    workflow.add_node("human_approval", human_approval_node)
    workflow.add_node("report", report_node)

    # 2. Build edges: Input guard -> Supervisor
    workflow.add_edge(START, "input_guard")
    workflow.add_edge("input_guard", "supervisor")

    # 3. Parallel Fan-Out from Supervisor to Specialists
    workflow.add_edge("supervisor", "metrics_agent")
    workflow.add_edge("supervisor", "logs_agent")
    workflow.add_edge("supervisor", "runbook_agent")

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
            "human_approval": "human_approval",
            "report": "report",
        },
    )
    workflow.add_edge("human_approval", "report")
    workflow.add_edge("report", END)

    return workflow


# Compiled graph singleton
incident_graph = build_incident_graph().compile()
