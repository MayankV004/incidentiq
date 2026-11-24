import json
import os
import statistics
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from mcp.server.mcpserver import MCPServer

from mcp_servers.validation import (
    ALLOWED_METRICS,
    ALLOWED_SERVICES,
    clamp_window,
    get_safe_scenario_path,
    sanitize_promql_service,
    validate_scenario_id,
    validate_service,
)

server = MCPServer("metrics_server")

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
DATA_MODE = os.getenv("DATA_MODE", "replay")
SCENARIO_ID = os.getenv("SCENARIO_ID", "001_orders_db_pool_exhaustion")


@server.tool()
def list_metrics(service: str) -> list[str]:
    """Returns the list of available allowed metric names for a given service."""
    if service and not validate_service(service):
        return []
    return ALLOWED_METRICS


def parse_metric_ts(ts_val: Any) -> datetime | None:
    """Parses metric timestamp safely into a timezone-aware datetime."""
    if not ts_val:
        return None
    try:
        if isinstance(ts_val, (int, float)):
            return datetime.fromtimestamp(ts_val, tz=UTC)
        clean = str(ts_val).replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except (ValueError, TypeError):
        return None


@server.tool()
def query_metric(
    service: str, metric: str, minutes: int = 30, scenario_id: str = ""
) -> dict[str, Any]:
    """Queries a specific metric for a service over a time window (minutes).

    Returns summary stats (min, max, mean, count) and downsampled points.
    """
    if not validate_service(service):
        return {
            "error": f"Invalid service '{service}'. Allowed services: {sorted(ALLOWED_SERVICES)}"
        }

    if metric not in ALLOWED_METRICS:
        return {
            "error": f"Metric '{metric}' is not allowed. Allowed metrics: {ALLOWED_METRICS}"
        }

    valid_minutes = clamp_window(minutes, max_minutes=180)
    data_mode = os.getenv("DATA_MODE", DATA_MODE)
    target_scenario = (
        scenario_id.strip()
        if scenario_id and scenario_id.strip()
        else os.getenv("SCENARIO_ID", SCENARIO_ID)
    )
    if not validate_scenario_id(target_scenario):
        return {"error": f"Invalid scenario_id '{target_scenario}': invalid path"}

    points: list[dict[str, Any]] = []

    if data_mode == "replay":
        safe_path = get_safe_scenario_path(target_scenario, "metrics.json")
        if safe_path and os.path.exists(safe_path):
            with open(safe_path) as f:
                raw = json.load(f)
                raw_service = raw.get("service")
                if raw_service and raw_service.strip().lower() != service.strip().lower():
                    points = []
                else:
                    points = raw.get("metrics", {}).get(metric, [])
        else:
            return {
                "error": f"Replay scenario '{target_scenario}' metrics not found or invalid path"
            }
    else:
        # Live Prometheus query fallback
        try:
            clean_srv = sanitize_promql_service(service)
            resp = httpx.get(
                f"{PROMETHEUS_URL}/api/v1/query_range",
                params={
                    "query": f"shop_{metric}{{service='{clean_srv}'}}",
                    "step": "15s",
                },
                timeout=3.0,
            )
            if resp.status_code == 200:
                result = resp.json().get("data", {}).get("result", [])
                if result:
                    points = [
                        {"timestamp": str(p[0]), "value": float(p[1])}
                        for p in result[0].get("values", [])
                    ]
        except (httpx.HTTPError, OSError) as e:
            return {"error": f"Prometheus query failed: {e}", "points": []}

    if points:
        parsed = [(parse_metric_ts(p.get("timestamp")), p) for p in points]
        valid_ts = [t for t, _ in parsed if t is not None]
        if valid_ts:
            if data_mode == "replay":
                max_ts = max(valid_ts)
            else:
                max_ts = datetime.now(UTC)
            cutoff = max_ts - timedelta(minutes=valid_minutes)
            points = [p for t, p in parsed if t is None or t >= cutoff]

    values = [float(p.get("value", 0.0)) for p in points]
    if not values:
        return {
            "service": service,
            "metric": metric,
            "summary": {"min": 0.0, "max": 0.0, "mean": 0.0, "count": 0},
            "points": [],
        }

    return {
        "service": service,
        "metric": metric,
        "summary": {
            "min": round(min(values), 4),
            "max": round(max(values), 4),
            "mean": round(statistics.mean(values), 4),
            "count": len(values),
        },
        "points": points[-60:],  # return up to 60 downsampled points
    }


@server.tool()
def detect_anomaly(
    service: str, metric: str, minutes: int = 30, scenario_id: str = ""
) -> dict[str, Any]:
    """Detects statistical anomalies for a given metric using mean and standard deviation."""
    query_res = query_metric(service, metric, minutes, scenario_id=scenario_id)
    if "error" in query_res:
        return query_res

    points = query_res.get("points", [])
    values = [float(p["value"]) for p in points if "value" in p]
    if len(values) < 5:
        return {
            "service": service,
            "metric": metric,
            "anomalous": False,
            "reason": "Insufficient points",
        }

    baseline = values[: len(values) // 2]
    recent = values[len(values) // 2 :]

    base_mean = statistics.mean(baseline)
    base_std = statistics.stdev(baseline) if len(baseline) > 1 else 0.1
    recent_mean = statistics.mean(recent)

    std_floor = max(base_std, base_mean * 0.05, 0.5)
    z_score = abs(recent_mean - base_mean) / std_floor
    relative_change = abs(recent_mean - base_mean) / (
        base_mean if base_mean > 0 else 1.0
    )

    is_anomaly = (z_score >= 2.5 and relative_change >= 0.10) or (
        max(recent) > base_mean * 1.5 and max(recent) > 1.0
    )

    return {
        "service": service,
        "metric": metric,
        "anomalous": is_anomaly,
        "z_score": round(z_score, 2),
        "baseline_mean": round(base_mean, 4),
        "recent_mean": round(recent_mean, 4),
        "severity": "high" if z_score >= 3.0 else ("medium" if is_anomaly else "low"),
    }


app = server.streamable_http_app()


if __name__ == "__main__":
    server.run()
