"""Unified Model Context Protocol (FastMCP) Client Adapter.

Enforces an allow-list wrapper in front of both in-process direct dispatch
and out-of-process Streamable HTTP MCP transport.
"""

import asyncio
import json
import logging
import os
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from incidentiq.agents.tool_registry import is_tool_allowed_for_agent
from mcp_servers.validation import validate_scenario_id

logger = logging.getLogger("incidentiq.mcp_client")

# In-process server instances and tool functions
from mcp_servers.logs.server import (
    get_error_clusters as inprocess_get_error_clusters,
)
from mcp_servers.logs.server import (
    get_log_context as inprocess_get_log_context,
)
from mcp_servers.logs.server import (
    search_logs as inprocess_search_logs,
)
from mcp_servers.metrics.server import (
    detect_anomaly as inprocess_detect_anomaly,
)
from mcp_servers.metrics.server import (
    list_metrics as inprocess_list_metrics,
)
from mcp_servers.metrics.server import (
    query_metric as inprocess_query_metric,
)
from mcp_servers.remediation.server import (
    restart_service as inprocess_restart_service,
)
from mcp_servers.remediation.server import (
    review_config as inprocess_review_config,
)
from mcp_servers.remediation.server import (
    rollback_deploy as inprocess_rollback_deploy,
)
from mcp_servers.remediation.server import (
    scale_up as inprocess_scale_up,
)

INPROCESS_TOOLS: dict[str, Any] = {
    "query_metric": inprocess_query_metric,
    "list_metrics": inprocess_list_metrics,
    "detect_anomaly": inprocess_detect_anomaly,
    "search_logs": inprocess_search_logs,
    "get_error_clusters": inprocess_get_error_clusters,
    "get_log_context": inprocess_get_log_context,
    "restart_service": inprocess_restart_service,
    "rollback_deploy": inprocess_rollback_deploy,
    "scale_up": inprocess_scale_up,
    "review_config": inprocess_review_config,
}

SERVER_URL_ENV_VARS = {
    "metrics": ("MCP_METRICS_URL", "http://mcp-metrics:9101/mcp"),
    "logs": ("MCP_LOGS_URL", "http://mcp-logs:9102/mcp"),
    "remediation": ("MCP_REMEDIATION_URL", "http://mcp-remediation:9103/mcp"),
}


async def _call_http_mcp(
    server_url: str, tool_name: str, arguments: dict[str, Any]
) -> Any:
    """Invokes a tool on a remote MCP server via Streamable HTTP transport."""
    async with (
        streamable_http_client(server_url) as (read, write),
        ClientSession(read, write) as session,
    ):
        await session.initialize()
        result = await session.call_tool(tool_name, arguments)

        # FastMCP structured_content preserves native types (dicts, lists)
        if (
            hasattr(result, "structured_content")
            and result.structured_content is not None
        ):
            if (
                isinstance(result.structured_content, dict)
                and "result" in result.structured_content
            ):
                return result.structured_content["result"]
            return result.structured_content

        if not result.content:
            return None

        if len(result.content) == 1:
            first_block = result.content[0]
            if hasattr(first_block, "text"):
                raw_text = first_block.text
                try:
                    return json.loads(raw_text)
                except (json.JSONDecodeError, ValueError):
                    return raw_text
            return first_block
        else:
            return [b.text if hasattr(b, "text") else b for b in result.content]


def call_mcp_tool(
    agent_name: str,
    server_name: str,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
) -> Any:
    """Unified entry-point for calling MCP tools.

    Enforces the agent's explicit tool allow-list before dispatching to either
    the in-process server or the Streamable HTTP client.
    """
    arguments = arguments or {}

    # 1. Enforce strict allow-list wrapper for both modes
    if not is_tool_allowed_for_agent(agent_name, tool_name):
        error_msg = f"Security Violation: Tool '{tool_name}' is not allowed for agent '{agent_name}'."
        logger.error(error_msg)
        raise PermissionError(error_msg)

    mcp_mode = os.getenv("MCP_MODE", "inprocess").lower()

    # 2. In-process dispatch (zero-overhead replay & local dev)
    if mcp_mode != "http":
        func = INPROCESS_TOOLS.get(tool_name)
        if not func:
            raise NotImplementedError(
                f"Tool '{tool_name}' not implemented in in-process registry"
            )
        return func(**arguments)

    # 3. Streamable HTTP client dispatch (production deploy compose)
    env_var, default_url = SERVER_URL_ENV_VARS.get(
        server_name, ("MCP_SERVER_URL", "http://127.0.0.1:9101/mcp")
    )
    server_url = os.getenv(env_var, default_url)

    try:
        # Check if an asyncio loop is already running in current thread
        loop = None
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            pass

        if loop and loop.is_running():
            # If called inside an existing async loop, run synchronously in a separate thread runner
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    asyncio.run, _call_http_mcp(server_url, tool_name, arguments)
                )
                return future.result(timeout=15)
        else:
            return asyncio.run(_call_http_mcp(server_url, tool_name, arguments))
    except Exception as exc:
        logger.error(f"HTTP MCP call to {server_url} for '{tool_name}' failed: {exc}")
        raise


# Convenience wrappers for specialist agents that route through call_mcp_tool
def _build_scenario_args(base: dict[str, Any], scenario_id: str = "") -> dict[str, Any]:
    clean_id = (scenario_id or "").strip()
    if clean_id:
        if not validate_scenario_id(clean_id):
            raise ValueError(f"Invalid scenario_id '{scenario_id}'")
        base["scenario_id"] = clean_id
    return base


def query_metric(
    service: str, metric: str, minutes: int = 30, scenario_id: str = ""
) -> dict[str, Any]:
    return call_mcp_tool(
        "metrics_agent",
        "metrics",
        "query_metric",
        _build_scenario_args(
            {"service": service, "metric": metric, "minutes": minutes}, scenario_id
        ),
    )


def list_metrics(service: str) -> list[str]:
    return call_mcp_tool(
        "metrics_agent", "metrics", "list_metrics", {"service": service}
    )


def detect_anomaly(
    service: str, metric: str, minutes: int = 30, scenario_id: str = ""
) -> dict[str, Any]:
    return call_mcp_tool(
        "metrics_agent",
        "metrics",
        "detect_anomaly",
        _build_scenario_args(
            {"service": service, "metric": metric, "minutes": minutes}, scenario_id
        ),
    )


def search_logs(
    service: str,
    query: str = "",
    level: str = "",
    minutes: int = 30,
    limit: int = 50,
    scenario_id: str = "",
) -> list[dict[str, Any]]:
    return call_mcp_tool(
        "logs_agent",
        "logs",
        "search_logs",
        _build_scenario_args(
            {
                "service": service,
                "query": query,
                "level": level,
                "minutes": minutes,
                "limit": limit,
            },
            scenario_id,
        ),
    )


def get_error_clusters(
    service: str, minutes: int = 30, scenario_id: str = ""
) -> list[dict[str, Any]]:
    return call_mcp_tool(
        "logs_agent",
        "logs",
        "get_error_clusters",
        _build_scenario_args({"service": service, "minutes": minutes}, scenario_id),
    )


def get_log_context(
    service: str, target_line_id: str, context: int = 5, scenario_id: str = ""
) -> list[str]:
    return call_mcp_tool(
        "logs_agent",
        "logs",
        "get_log_context",
        _build_scenario_args(
            {"service": service, "target_line_id": target_line_id, "context": context},
            scenario_id,
        ),
    )


def restart_service(
    service: str, token: str = "", approval_token: str = "", incident_id: str = ""
) -> dict[str, Any]:
    t = token or approval_token
    return call_mcp_tool(
        "remediation",
        "remediation",
        "restart_service",
        {"service": service, "token": t, "incident_id": incident_id},
    )


def rollback_deploy(
    service: str,
    target_version: str = "v1.0.0",
    token: str = "",
    approval_token: str = "",
    incident_id: str = "",
) -> dict[str, Any]:
    t = token or approval_token
    return call_mcp_tool(
        "remediation",
        "remediation",
        "rollback_deploy",
        {
            "service": service,
            "target_version": target_version,
            "token": t,
            "incident_id": incident_id,
        },
    )


def scale_up(
    service: str,
    replicas: int = 3,
    token: str = "",
    approval_token: str = "",
    incident_id: str = "",
) -> dict[str, Any]:
    t = token or approval_token
    return call_mcp_tool(
        "remediation",
        "remediation",
        "scale_up",
        {
            "service": service,
            "replicas": replicas,
            "token": t,
            "incident_id": incident_id,
        },
    )


def review_config(
    service: str,
    parameter: str = "config",
    proposed_value: str = "",
    token: str = "",
    incident_id: str = "",
    detail: str = "",
) -> dict[str, Any]:
    return call_mcp_tool(
        "remediation",
        "remediation",
        "review_config",
        {
            "service": service,
            "parameter": parameter or detail or "config",
            "proposed_value": proposed_value or "updated",
            "token": token,
            "incident_id": incident_id,
        },
    )
