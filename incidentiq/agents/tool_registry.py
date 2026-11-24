"""Tool allow-list specifications and enforcement for IncidentIQ agents."""

AGENT_TOOL_ALLOWLISTS: dict[str, set[str]] = {
    "metrics_agent": {"query_metric", "list_metrics", "detect_anomaly"},
    "logs_agent": {"search_logs", "get_error_clusters", "get_log_context"},
    "runbook_agent": {"search_knowledge_base", "retrieve_runbooks"},
    "root_cause_agent": set(),
    "remediation": {
        "restart_service",
        "rollback_deploy",
        "scale_up",
        "review_config",
    },
}


def is_tool_allowed_for_agent(agent_name: str, tool_name: str) -> bool:
    """Verifies that a tool is on the agent's explicit cryptographic/code allow-list."""
    allowed = AGENT_TOOL_ALLOWLISTS.get(agent_name, set())
    return tool_name in allowed
