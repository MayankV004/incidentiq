import os
import threading
import time

import pytest
import uvicorn

from incidentiq.agents.mcp_client import call_mcp_tool
from mcp_servers.metrics.server import app as metrics_app


@pytest.fixture(scope="module")
def run_mcp_http_server():
    """Runs a real FastMCP Streamable HTTP server in a background thread."""
    host = "127.0.0.1"
    port = 9198
    config = uvicorn.Config(metrics_app, host=host, port=port, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    time.sleep(1)

    old_mode = os.environ.get("MCP_MODE")
    old_url = os.environ.get("MCP_METRICS_URL")
    os.environ["MCP_MODE"] = "http"
    os.environ["MCP_METRICS_URL"] = f"http://{host}:{port}/mcp"

    yield f"http://{host}:{port}/mcp"

    server.should_exit = True
    if old_mode is not None:
        os.environ["MCP_MODE"] = old_mode
    else:
        os.environ.pop("MCP_MODE", None)

    if old_url is not None:
        os.environ["MCP_METRICS_URL"] = old_url
    else:
        os.environ.pop("MCP_METRICS_URL", None)


def test_real_mcp_http_client_call(run_mcp_http_server):
    """Verifies tool execution over real Streamable HTTP transport with MCP ClientSession."""
    result = call_mcp_tool(
        agent_name="metrics_agent",
        server_name="metrics",
        tool_name="list_metrics",
        arguments={"service": "orders"},
    )
    assert isinstance(result, list)
    assert "db_pool_in_use" in result


def test_allowlist_wrapper_blocks_forbidden_tools(run_mcp_http_server):
    """Verifies that the unified allow-list wrapper intercepts unauthorized tools in HTTP mode."""
    with pytest.raises(PermissionError) as exc_info:
        call_mcp_tool(
            agent_name="metrics_agent",
            server_name="remediation",
            tool_name="restart_service",
            arguments={"service": "orders", "approval_token": "fake"},
        )
    assert "not allowed for agent" in str(exc_info.value)


def test_allowlist_wrapper_blocks_unauthorized_agent(run_mcp_http_server):
    """Verifies that an agent with empty allowlist cannot invoke metrics tools."""
    with pytest.raises(PermissionError) as exc_info:
        call_mcp_tool(
            agent_name="root_cause_agent",
            server_name="metrics",
            tool_name="query_metric",
            arguments={"service": "orders", "metric": "db_pool_in_use"},
        )
    assert "not allowed for agent" in str(exc_info.value)
