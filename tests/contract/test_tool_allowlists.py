"""Contract test verifying agent tool sets match Document 06 specifications."""

from incidentiq.agents.tool_registry import (
    AGENT_TOOL_ALLOWLISTS,
    is_tool_allowed_for_agent,
)


def test_agent_tool_allowlists_match_document_06():
    # Document 06 Section 5 exact contract
    expected_metrics_tools = {"query_metric", "list_metrics", "detect_anomaly"}
    expected_logs_tools = {"search_logs", "get_error_clusters", "get_log_context"}
    expected_runbook_tools = {"search_knowledge_base", "retrieve_runbooks"}
    expected_root_cause_tools = set()
    expected_remediation_tools = {
        "restart_service",
        "rollback_deploy",
        "scale_up",
        "review_config",
    }

    assert AGENT_TOOL_ALLOWLISTS["metrics_agent"] == expected_metrics_tools
    assert AGENT_TOOL_ALLOWLISTS["logs_agent"] == expected_logs_tools
    assert AGENT_TOOL_ALLOWLISTS["runbook_agent"] == expected_runbook_tools
    assert AGENT_TOOL_ALLOWLISTS["root_cause_agent"] == expected_root_cause_tools
    assert AGENT_TOOL_ALLOWLISTS["remediation"] == expected_remediation_tools


def test_forbidden_tool_access_rejected_in_code():
    # 1. Metrics agent cannot invoke remediation or logs
    assert not is_tool_allowed_for_agent("metrics_agent", "restart_service")
    assert not is_tool_allowed_for_agent("metrics_agent", "search_logs")
    assert is_tool_allowed_for_agent("metrics_agent", "query_metric")

    # 2. Logs agent cannot invoke remediation or metrics
    assert not is_tool_allowed_for_agent("logs_agent", "rollback_deploy")
    assert not is_tool_allowed_for_agent("logs_agent", "query_metric")
    assert is_tool_allowed_for_agent("logs_agent", "search_logs")

    # 3. Root cause agent has empty tool set (pure synthesis)
    assert not is_tool_allowed_for_agent("root_cause_agent", "restart_service")
    assert not is_tool_allowed_for_agent("root_cause_agent", "query_metric")
    assert not is_tool_allowed_for_agent("root_cause_agent", "search_logs")
