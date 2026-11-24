import json
import os
import re
from datetime import UTC, datetime, timedelta
from typing import Any

from mcp.server.mcpserver import MCPServer

from mcp_servers.validation import (
    ALLOWED_SERVICES,
    clamp_context,
    clamp_limit,
    clamp_window,
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


def parse_iso_ts(ts_str: Any) -> datetime | None:
    """Parses ISO timestamp string safely into a timezone-aware datetime."""
    if not ts_str or not isinstance(ts_str, str):
        return None
    try:
        clean = ts_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except (ValueError, TypeError):
        return None


def load_raw_logs(service: str, minutes: int | None = None) -> list[dict[str, Any]]:
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
                            entry = json.loads(line)
                            if not service or entry.get("service") == service:
                                logs.append(entry)
                        except json.JSONDecodeError:
                            continue

    if minutes is not None and logs:
        valid_minutes = clamp_window(minutes)
        parsed = [(parse_iso_ts(l.get("ts")), l) for l in logs]
        valid_ts = [t for t, _ in parsed if t is not None]
        if valid_ts:
            if data_mode == "replay":
                max_ts = max(valid_ts)
            else:
                max_ts = datetime.now(UTC)
            cutoff = max_ts - timedelta(minutes=valid_minutes)
            logs = [l for t, l in parsed if t is None or t >= cutoff]

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
        return [
            {
                "error": f"Invalid service '{service}'. Allowed services: {sorted(ALLOWED_SERVICES)}"
            }
        ]

    valid_minutes = clamp_window(minutes)
    capped_limit = clamp_limit(limit, max_limit=50)

    raw_logs = load_raw_logs(service, minutes=valid_minutes)
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
        if len(results) >= capped_limit:
            break

    return results


@server.tool()
def get_error_clusters(service: str, minutes: int = 30) -> list[dict[str, Any]]:
    """Groups similar error log messages into clusters with occurrence count and first/last seen timestamps."""
    if service and not validate_service(service):
        return [
            {
                "error": f"Invalid service '{service}'. Allowed services: {sorted(ALLOWED_SERVICES)}"
            }
        ]

    valid_minutes = clamp_window(minutes)
    raw_logs = load_raw_logs(service, minutes=valid_minutes)
    clusters: dict[str, dict[str, Any]] = {}

    for log in raw_logs:
        if log.get("level", "").lower() not in ["error", "fatal", "critical"]:
            continue

        msg = log.get("msg", "")
        # Normalize message pattern by removing UUIDs, digits, and specific hashes
        pattern = re.sub(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            "<UUID>",
            msg,
        )
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
def get_log_context(
    service: str, line_id: str = "", before: int = 5, after: int = 5
) -> dict[str, Any]:
    """Returns surrounding log context around an error line."""
    if service and not validate_service(service):
        return {
            "service": service,
            "context_lines": [],
            "error": f"Invalid service '{service}'",
        }

    safe_before = clamp_context(before, max_context=20)
    safe_after = clamp_context(after, max_context=20)

    raw_logs = load_raw_logs(service)
    target_idx = None

    if line_id:
        line_clean = str(line_id).strip()
        for idx, entry in enumerate(raw_logs):
            if (
                entry.get("request_id") == line_clean
                or entry.get("ts") == line_clean
                or line_clean in entry.get("msg", "")
                or str(idx) == line_clean
            ):
                target_idx = idx
                break

    if target_idx is not None:
        start_idx = max(0, target_idx - safe_before)
        end_idx = min(len(raw_logs), target_idx + safe_after + 1)
        slice_logs = raw_logs[start_idx:end_idx]
    else:
        slice_logs = raw_logs[: (safe_before + safe_after)]

    return {
        "service": service,
        "target_id": line_id,
        "context_lines": [wrap_untrusted(l.get("msg", "")) for l in slice_logs],
    }


app = server.streamable_http_app()


if __name__ == "__main__":
    server.run()
