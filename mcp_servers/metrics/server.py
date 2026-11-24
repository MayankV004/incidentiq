import json
import os
import statistics
from typing import Any

import httpx
from mcp.server.mcpserver import MCPServer

from mcp_servers.validation import (
    ALLOWED_METRICS,
    ALLOWED_SERVICES,
    get_safe_scenario_path,
    sanitize_promql_service,
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


@server.tool()
def query_metric(service: str, metric: str, minutes: int = 30) -> dict[str, Any]:
    """Queries a specific metric for a service over a time window (minutes).

    Returns summary stats (min, max, mean, count) and downsampled points.
    """
    if not validate_service(service):
        return {"error": f"Invalid service '{service}'. Allowed services: {sorted(ALLOWED_SERVICES)}"}

    if metric not in ALLOWED_METRICS:
        return {"error": f"Metric '{metric}' is not allowed. Allowed metrics: {ALLOWED_METRICS}"}

    data_mode = os.getenv("DATA_MODE", DATA_MODE)
    scenario_id = os.getenv("SCENARIO_ID", SCENARIO_ID)

    points: list[dict[str, Any]] = []

    if data_mode == "replay":
        safe_path = get_safe_scenario_path(scenario_id, "metrics.json")
        if safe_path and os.path.exists(safe_path):
            with open(safe_path) as f:
                raw = json.load(f)
                points = raw.get("metrics", {}).get(metric, [])
        else:
            return {"error": f"Replay scenario '{scenario_id}' metrics not found or invalid path"}
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
                    points = [{"timestamp": str(p[0]), "value": float(p[1])} for p in result[0].get("values", [])]
        except (httpx.HTTPError, OSError) as e:
            return {"error": f"Prometheus query failed: {e}", "points": []}

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
        "points": points[-30:],  # return latest 30 points
    }


@server.tool()
def detect_anomaly(service: str, metric: str, minutes: int = 30) -> dict[str, Any]:
    """Detects statistical anomalies for a given metric using mean and standard deviation."""
    query_res = query_metric(service, metric, minutes)
    if "error" in query_res:
        return query_res

    points = query_res.get("points", [])
    values = [float(p["value"]) for p in points if "value" in p]
    if len(values) < 5:
        return {"service": service, "metric": metric, "anomalous": False, "reason": "Insufficient points"}

    baseline = values[: len(values) // 2]
    recent = values[len(values) // 2 :]

    base_mean = statistics.mean(baseline)
    base_std = statistics.stdev(baseline) if len(baseline) > 1 else 0.1
    recent_mean = statistics.mean(recent)

    std_floor = max(base_std, base_mean * 0.05, 0.5)
    z_score = abs(recent_mean - base_mean) / std_floor
    relative_change = abs(recent_mean - base_mean) / (base_mean if base_mean > 0 else 1.0)

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


if __name__ == "__main__":
    server.run()
