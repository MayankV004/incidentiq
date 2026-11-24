import json
import os
import re
from typing import Any

from mcp.server.mcpserver import MCPServer

from mcp_servers.validation import (
    ALLOWED_SERVICES,
    get_safe_log_path,
    get_safe_scenario_path,
    validate_service,
)

server = MCPServer("logs_server")

DATA_MODE = os.getenv("DATA_MODE", "replay")
SCENARIO_ID = os.getenv("SCENARIO_ID", "001_orders_db_pool_exhaustion")


def wrap_untrusted(text: str) -> str:
    """Wraps raw log content in untrusted_data tags to defend against prompt injection."""
    return f"<untrusted_data>\n{text}\n</untrusted_data>"


def load_raw_logs(service: str) -> list[dict[str, Any]]:
    if service and not validate_service(service):
        return []

    data_mode = os.getenv("DATA_MODE", DATA_MODE)
    scenario_id = os.getenv("SCENARIO_ID", SCENARIO_ID)

    logs: list[dict[str, Any]] = []
    if data_mode == "replay":
        safe_path = get_safe_scenario_path(scenario_id, "logs.jsonl")
        if safe_path and os.path.exists(safe_path):
            with open(safe_path) as f:
                for line in f:
                    if line.strip():
                        try:
                            entry = json.loads(line)
                            if not service or entry.get("service") == service:
                                logs.append(entry)
                        except json.JSONDecodeError:
                            continue
    else:
        # Live log file
        log_file = get_safe_log_path(service)
        if log_file and os.path.exists(log_file):
            with open(log_file) as f:
                for line in f:
                    if line.strip():
                        try:
                            logs.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
    return logs


@server.tool()
def search_logs(
    service: str,
    query: str = "",
    level: str = "",
    minutes: int = 30,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Searches logs for a service by substring query and log level.

    Returned log content is strictly wrapped as untrusted data to mitigate indirect prompt injection.
    """
    if service and not validate_service(service):
        return [{"error": f"Invalid service '{service}'. Allowed services: {sorted(ALLOWED_SERVICES)}"}]
    raw_logs = load_raw_logs(service)
    results = []

    for log in raw_logs:
        msg = log.get("msg", "")
        log_level = log.get("level", "").lower()

        if level and log_level != level.lower():
            continue
        if query and query.lower() not in msg.lower():
            continue

        results.append(
            {
                "ts": log.get("ts"),
                "level": log.get("level"),
                "service": log.get("service"),
                "msg": wrap_untrusted(msg[:300]),  # truncate and wrap
                "request_id": log.get("request_id"),
            }
        )
        if len(results) >= limit:
            break

    return results


@server.tool()
def get_error_clusters(service: str, minutes: int = 30) -> list[dict[str, Any]]:
    """Groups similar error log messages into clusters with occurrence count and first/last seen timestamps."""
    if service and not validate_service(service):
        return [{"error": f"Invalid service '{service}'. Allowed services: {sorted(ALLOWED_SERVICES)}"}]
    raw_logs = load_raw_logs(service)
    clusters: dict[str, dict[str, Any]] = {}

    for log in raw_logs:
        if log.get("level", "").lower() not in ["error", "fatal", "critical"]:
            continue

        msg = log.get("msg", "")
        # Normalize message pattern by removing UUIDs, digits, and specific hashes
        pattern = re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "<UUID>", msg)
        pattern = re.sub(r"\d+", "<N>", pattern)
        pattern = pattern[:150]

        ts = log.get("ts", "")
        if pattern not in clusters:
            clusters[pattern] = {
                "pattern": wrap_untrusted(pattern),
                "count": 0,
                "first_seen": ts,
                "last_seen": ts,
                "example": wrap_untrusted(msg[:200]),
            }
        clusters[pattern]["count"] += 1
        clusters[pattern]["last_seen"] = ts

    sorted_clusters = sorted(clusters.values(), key=lambda c: c["count"], reverse=True)
    return sorted_clusters[:10]


@server.tool()
def get_log_context(service: str, line_id: str = "", before: int = 5, after: int = 5) -> dict[str, Any]:
    """Returns surrounding log context around an error line."""
    if service and not validate_service(service):
        return {"service": service, "context_lines": [], "error": f"Invalid service '{service}'"}
    raw_logs = load_raw_logs(service)
    return {
        "service": service,
        "context_lines": [wrap_untrusted(l.get("msg", "")) for l in raw_logs[: (before + after)]],
    }


if __name__ == "__main__":
    server.run()
